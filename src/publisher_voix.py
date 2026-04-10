import json
import os
import platform
import random
import subprocess
import sys
import time
import unicodedata
import re
from datetime import datetime, timezone
from french_lefff_lemmatizer.french_lefff_lemmatizer import FrenchLefffLemmatizer
import speech_recognition as sr
import paho.mqtt.client as mqtt
from joblib import Memory
import client_utils
import gpio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main_utils
from db import db_utils
mode_nuit_state = False
state_led = False
config = main_utils.get_config()
BROKER_HOST = config["BROKER_HOST"]
BROKER_PORT = config["BROKER_PORT_LOCAL"]
MIC_INDEX = 1
hotword = "raspi"
topic = "maison/voix"
rec_liste = {
    "oui": ["./aiff/aff.aiff"],#"Oui"
    "non": ["./aiff/aff.neg"],#"Non"
    "ecoute": ["./aiff/ecoute.aiff", "./aiff/ecoute2.aiff"], #"Je vous écoute" "Oui?"
    "on": ["./aiff/lampon.aiff", "./aiff/lampon2.aiff","./aiff/lampon3.aiff"],# "Lampe allumée"#"J'ai allumée la lampe"
    "off": ["./aiff/lampoff.aiff", "./aiff/lampoff2.aiff", "./aiff/lampoff3.aiff"],# "J'ai éteint la lampe" "La lampe est éteint" "lampe éteint"
    "nuit_on": ["./aiff/nuiton.aiff"],#"J'ai activé la mode nuit"
    "nuit_off": ["./aiff/nuitoff.aiff"],#"J'ai desactivé la mode nuit"
    "cling": ["./aiff/cling.aiff"],#"Je clignote la lampe"
    "error": ["./aiff/error.aiff", "./aiff/error2.aiff","./aiff/error3.aiff"]}#"Je ne comprends pas"# Veuillez repeter"#"Je n'ai pas compris"#"Répétez, s'il vous plaît"

def detect_hotword(text):
    if hotword in text:
        return True
    return None

memory = Memory("cachedir", verbose=0)
@memory.cache
# @lru_cache(maxsize=100)
def cached_lemmantizer(word):
    return lemmatizer.lemmatize(word)


lemmatizer = FrenchLefffLemmatizer()
regex_pattern = re.compile(r"[^\W\d_]+", flags=re.UNICODE)
stopwords = {"la", "le", "les", "dans", "a", "de", "des", "et", "un", "une", "l"}
def voix_normalise(text):
    """
    nomalise un texte en lema
    return: list of normalized words
    """

    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    words = regex_pattern.findall(text.lower())
    return [cached_lemmantizer(word) for word in words if word not in stopwords]

def listen(timeout=5):
    """
    wait for speech input
    return: list of normalized words
    """
    mic = sr.Microphone(device_index=MIC_INDEX)
    r = sr.Recognizer()
    r.dynamic_energy_threshold = False
    r.energy_threshold = 10000
    r.pause_threshold = 1

    with mic as source:
        print("ajustement de l'environnement")
        r.adjust_for_ambient_noise(source, duration=1)
        print("seuil energie calibre = ", r.energy_threshold)
        print("parlez maintenant....")
        while True:

            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=5)
            except sr.WaitTimeoutError:
                print("Timeout")
                continue
            try:
                text = r.recognize_google(audio, language="fr-FR")
                print(f"Vous avez dit : {text}")
                return voix_normalise(text)

            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")

def wait_for_hotword():
    tokens = listen()
    if tokens is None:
        return None
    if any(item in tokens for item in ["raspi", "raspberry", "pi"]):
            print("Hotword detected")
            return True
    return None

def categorise_command(tokens: list):
    if not tokens:
        return None
    if "etat" in tokens:
        if any(item in tokens for item in ["mode", "nuit"]):
            respond("none", text=f"mode nuit est {'actif' if mode_nuit_state else 'inactif'}")
            return config["topic"]["etat"], "nuit"
        else:
            respond("none", f"la lampe est {'on' if state_led else 'off'}")
            db_utils.insert_event(f"{state_led}", topic="demande état lampe")
            return None
    if any(item in tokens for item in ["temperature", "cpu"]):
        respond("none", text=f"la temperature est {gpio.cpu_temp()} Celsius")
        return config["topic"]["etat"], "temp"
    if any(item in tokens for item in ["allumer", "on", "activer", "active"]):
        cmd = "ON"
    elif any(item in tokens for item in ["desactiver", "off", "eteint"]):
        cmd = "OFF"
    else:
        cmd = "error"

    if any(item in tokens for item in ["mode", "nuit"]):
        if cmd == "ON":
            respond("nuit_on")
            print("mode nuit on")
        elif cmd == "OFF":
            respond("nuit_off")
            print("mode nuit off")
        return config["topic"]["nuit"], cmd

    if "clignote" in tokens:
        if cmd == "ON" or cmd == "error":
            cmd = "ON"
            respond("cling")
            print("clignote")
        return config["topic"]["cling"], cmd

    if any(item in tokens for item in ["lumiere", "lampe", "del", "led"]):
        if cmd == "ON":
            respond("ON")
            print("allume la lampe")
        elif cmd == "OFF":
            respond("OFF")
            print("eteint la lampe")
        return config["topic"]["led_command"], cmd

    respond("error")
    print("je ne comprends pas")
    return config["topic"]["error"] , "object"

def wait_for_command():
    words = listen()
    if words is None:
        return None
    return categorise_command(words)

def listen_loop():
    while True:
        if wait_for_hotword():
            command = wait_for_command()
            if command is not None:
                return command

system_name = platform.system().lower()

def speak(text, lang="fr", speed=150):
    if system_name == "darwin":
        subprocess.run(["say", "-v", "amélie", text])
    else:
        try:
            subprocess.run(["espeak-ng", "-v", lang, "-s", str(speed), text])
        except FileNotFoundError:
            print("espeak-ng not found, using say instead")

def play(file):
    file_path = main_utils.abs_path(file)
    if not os.path.exists(file_path):
        print(f"File {file_path} not found")
        return
    if system_name == "darwin":
        subprocess.run(["afplay", file_path])
    else:
        try:
            subprocess.run(["aplay", file_path])
        except FileNotFoundError:
            print("aplay not found")

def respond(category, text=""):
    if category in rec_liste:
        play(random.choice(rec_liste[category]))
    elif text:
        speak(text)
    else:
        play(random.choice(rec_liste["error"]))

# def cache_audio():
#     """
#     pour cacher les fichiers audio avec le text propre
#     """
#     return


client = mqtt.Client(
    client_id=config["client_id_pub_voix"],
    callback_api_version = mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(username=config["user"], password=config["password"])

client.will_set(
    topic=config["TOPICS"]["presence_voix"],
    payload=json.dumps({"presence" : "offline"}),
    qos=1,
    retain=True)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[INFO] Voix Connected")
        client.subscribe(config["TOPICS"]["mode_nuit"], qos=1)
        client.subscribe(config["TOPICS"]["led_status"], qos=1)

    else:
        print(f"[ERROR] Voix Connection failed with code {rc}")
        exit(1)


def on_message(client, userdata, msg):
    classification = client_utils.classify_kind(msg.topic)
    # print(f"[MSG] raw_message={msg.payload} classification={classification}")
    payload = msg.payload.decode("utf-8", errors="replace")

    print(
        f"[MSG] topic={msg.topic} "
        f"qos={msg.qos} retain={msg.retain} "
        f"payload={payload}")
    if "etat" in msg.topic:
        if payload["state"] == "ON":
            led_status = True
        elif payload["state"] == "OFF":
            led_status = False
    if "mode_nuit/state" in msg.topic:
        if payload["state"] == "ON":
            mode_nuit_status = True
        elif payload["state"] == "OFF":
            mode_nuit_status = False


client.on_connect = on_connect
client.on_disconnect = client_utils.on_disconnect

client.connect(host=config["BROKER_HOST"], port=config["BROKER_PORT_LOCAL"], keepalive=config["KEEPALIVE_SECONDS"])

client.loop_start()

result = client.publish(
    topic=config["TOPICS"]["presence_voix"],
    payload = json.dumps({"presence" : "online"}),
    qos=1,
    retain=True)

result.wait_for_publish()

try:
    while True:
        topic, command = listen_loop()
        # if topic is config["topic"]["led_command"]:
        payload = {command}
        # else:
        #     payload = {
        #         "device": config["device_id"],
        #         "sensor": "microphone",
        #         "value": command,  # valeur numerique
        #         "ts": datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}

        # Publication de la mesure
        if command is not None:
            client.publish(
                topic=topic,
                payload=json.dumps(payload),  # dict Python -> string JSON
                qos=1,
                retain=False)
            # db_utils.insert_measurement(json.dumps(payload), topic=topic)
            print(f"[PUB] {config["TOPICS"]["command_voix"]} -> {payload}")

            # time.sleep(config["measure_interval"])

except KeyboardInterrupt:
    print("\n[STOP] arrêt demande")
finally:
    try:
        result = client.publish(
            topic=config["TOPICS"]["presence_voix"],
            payload=json.dumps({"presence": "offline"}),
            qos=1,
            retain=True,
        )
        result.wait_for_publish(timeout=5)
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        try:
            client.loop_stop()
        except KeyboardInterrupt:
            pass
        except Exception:
            pass
    sys.exit(0)


if __name__ == "__main__":
    print(
        voix_normalise("allume la lampe éteins la lampe fais clignoter la lampe donne-moi l’état active le mode nuit"))

    # respond("speak", "Bonjour, je suis la voix de ma maison")
