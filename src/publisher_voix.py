import json
import os
import platform
import random
import subprocess
import sys
import unicodedata
import re
from datetime import datetime, timezone

from french_lefff_lemmatizer.french_lefff_lemmatizer import FrenchLefffLemmatizer
import speech_recognition as sr
import paho.mqtt.client as mqtt
from joblib import Memory
import client_utils
import gpio
from client_utils import classify_kind
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main_utils
from db import db_utils

led_state = "La lampe est éteint"
mode_nuit_state = "La mode nuit n'est pas actif"
msg_led_on = "La lampe est allume"
msg_led_off = "La lampe est éteint"
msg_mode_nuit_on = "La mode nuit est actif"
msg_mode_nuit_off = "La mode nuit n'est pas actif"
config = main_utils.get_config()
MIC_INDEX = 1



rec_liste = {
    "oui": ["./aiff/aff.aiff"],#"Oui"
    "non": ["./aiff/neg.aiff"],#"Non"
    "ecoute": ["./aiff/ecoute.aiff", "./aiff/ecoute2.aiff"], #"Je vous écoute" "Oui?"
    "on": ["./aiff/lampeon.aiff", "./aiff/lampeon2.aiff","./aiff/lampeon3.aiff"],# "Lampe allumée"#"J'ai allumée la lampe"
    "off": ["./aiff/lampeoff1.aiff", "./aiff/lampeoff2.aiff", "./aiff/lampeoff3.aiff"],# "J'ai éteint la lampe" "La lampe est éteint" "lampe éteint"
    "nuit_on": ["./aiff/modenuiton.aiff"],#"J'ai activé la mode nuit"
    "nuit_off": ["./aiff/modenuitoff.aiff"],#"J'ai desactivé la mode nuit"
    "cling": ["./aiff/clng.aiff"],#"Je clignote la lampe"
    "error": ["./aiff/err.aiff", "./aiff/err2.aiff","./aiff/err3.aiff"]}#"Je ne comprends pas"# Veuillez repeter"#"Je n'ai pas compris"#"Répétez, s'il vous plaît"


memory = Memory("cachedir", verbose=0)
@memory.cache
# @lru_cache(maxsize=100)
def cached_lemmantizer(word):
    return lemmatizer.lemmatize(word)

# Speech Recognition
lemmatizer = FrenchLefffLemmatizer() # plus specialise au francais que les outills de nltk
regex_pattern = re.compile(r"[^\W\d_]+", flags=re.UNICODE)
mic = None
r = None
hotwords = ["bonjour", "maison"]
stopwords = {"la", "le", "les", "dans", "a", "de", "des", "et", "un", "une", "l"}
def voix_normalise(text):
    """
    nomalise un texte en lema
    return: list of normalized words
    """

    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    words = regex_pattern.findall(text.lower())
    return [cached_lemmantizer(word) for word in words if word not in stopwords]

def init_mic():
    global mic, r
    print("initialisation du microphone...")
    mic = sr.Microphone(device_index=MIC_INDEX)
    r = sr.Recognizer()
    r.dynamic_energy_threshold = False
    r.energy_threshold = 300
    r.pause_threshold = 1
    with mic as source:
        print("ajustement de l'environnement")
        r.adjust_for_ambient_noise(source, duration=2)
        print("seuil energie calibre = ", r.energy_threshold)
        print("parlez maintenant....")
    return mic, r

def listen(timeout=1):
    """
    wait for speech input
    return: list of normalized words
    """
    global mic, r
    if mic is None or r is None:
        mic, r = init_mic()
    with mic as source:
        print("[INFO] listening...")
        try:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=4)
        except sr.WaitTimeoutError:
            return None
        try:
            print("recogniser...")
            text = r.recognize_google(audio, language="fr-FR")
            print(f"Vous avez dit : {text}")
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return None

def wait_for_hotword():
    text = listen()
    if text is None:
        print("[INFO] No speech detected")
        return False

    tokens = voix_normalise(text)
    print(f"hotwords are {hotwords} detection: text: {text}, tokens:{tokens}")

    for hotword in hotwords:
        if (hotword.lower().strip() in [t.lower().strip for t in tokens]
                or hotword.lower().strip() in text.lower().strip()):
            print("[INFO] Hotword detected")
            return True
    print("[INFO] Hotword not detected")
    return False

def log_event(device, actuator, state, topic):
    payload = {
        "device": device,
        "actuator": actuator,
        "state": state,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    }
    print(f"[DEBUG] Logging event: {payload} to topic: {topic}")
    db_utils.insert_event(json.dumps(payload), topic=topic)

def categorise_command(tokens: list):
    """categorize a vox command"""
    global mode_nuit_state, led_state
    if not tokens:
        return None
    # status commands
    if any(item in tokens for item in ["etat", "etats", "status", "statut"]):
        if any(item in tokens for item in ["mode", "nuit"]):
            respond("none", text=mode_nuit_state)
            log_event(config["device_id"], f"Vox", f"demande status mode nuit: {mode_nuit_state}", config["TOPICS"]["vox"])
            return None, None
        else:
            respond("none", led_state)
            log_event(config["device_id"], f"Vox", f"demande status lampe: {led_state}", config["TOPICS"]["vox"])
            return None, None
    if any(item in tokens for item in ["temperature", "cpu"]):
        temp = round(gpio.cpu_temp())
        respond("none", text=f"la temperature est {temp} Celsius")
        log_event(config["device_id"], f"Vox", f"demande temp: {temp} Celsius",
                  config["TOPICS"]["vox"])
        return None, None

    # action commands
    # states
    if any(item in tokens for item in ["allumer", "on", "activer", "active", "allume"]):
        cmd = "ON"
    elif any(item in tokens for item in ["desactiver", "off", "eteint", "eteins", "etein"]):
        cmd = "OFF"
    else:
        cmd = "error"

    # Objects
    if any(item in tokens for item in ["mode", "nuit"]):
        if cmd == "ON":
            if mode_nuit_state == msg_mode_nuit_off:
                respond("nuit_on")
                print("mode nuit on")
            else:
                respond("none", text=mode_nuit_state)
        elif cmd == "OFF":
            if mode_nuit_state == msg_mode_nuit_on:
                respond("nuit_off")
                print("mode nuit off")
            else:
                respond("none", text=mode_nuit_state)

        log_event(config["device_id"], f"Vox", f"cmd mode nuit: {cmd}",
                  config["TOPICS"]["vox"])
        return config["TOPICS"]["mode_nuit"], cmd

    if "clignote" in tokens:
        if cmd == "ON" or cmd == "OFF": #pour pouvoir toggle pour le moment
            respond("cling")
            print("clignote")

        log_event(config["device_id"], f"Vox", f"demande toggle led clignote",
                  config["TOPICS"]["vox"])
        return config["TOPICS"]["led_cling"], cmd

    if any(item in tokens for item in ["lumiere", "lampe", "del", "led"]):
        if cmd == "ON":
            if led_state == msg_led_off:
                respond("on")
                print("allume la lampe")
            else:
                respond("none", text=led_state)
        elif cmd == "OFF":
            if led_state == msg_led_on:
                respond("off")
                print("éteint la lampe")
            else:
                respond("none", text=led_state)

        log_event(config["device_id"], f"Vox", f"demande toggle lampe: {cmd}",
                  config["TOPICS"]["vox"])
        return config["TOPICS"]["led_command"], cmd

    respond("error")
    print("je ne comprends pas")
    log_event(config["device_id"], f"Vox", f"commande non compris", config["TOPICS"]["vox"])
    return config["TOPICS"]["error"] , "error"

def wait_for_command():
    text = listen(timeout=8)
    if text is None:
        return None, None
    tokens = voix_normalise(text)
    print(f"tokens: {tokens}")
    return categorise_command(tokens)

system_name = platform.system().lower()

def speak(text, lang="fr", speed=150):
    """
    tts
    """
    if system_name == "darwin":
        subprocess.run(["say", "-v", "amélie", text], check=True)
    else:
        try:
            subprocess.run(["espeak-ng", "-v", lang, "-s", str(speed), text], check=True)
        except FileNotFoundError:
            print("espeak-ng not found, using say instead")

# tts functions
def play(file):
    """
    play a file
    no return value
    """
    file_path = main_utils.abs_path(file)
    if not os.path.exists(file_path):
        print(f"File {file_path} not found")
        return
    if system_name == "darwin":
        subprocess.run(["afplay", file_path], check=True)
    else:
        try:
            subprocess.run(["ffplay", "-nodisp", "-autoexit", file_path], check=True)
        except FileNotFoundError:
            print("aplay not found")

def respond(category, text=""):
    """
    respond to a command
    no return value
    """
    if category in rec_liste:
        play(random.choice(rec_liste[category]))
    elif text:
        speak(text)
    else:
        play(random.choice(rec_liste["error"]))

client = mqtt.Client(
    client_id=config["client_id_vox"],
    callback_api_version = mqtt.CallbackAPIVersion.VERSION2)

client.will_set(
    topic=config["TOPICS"]["presence_voix"],
    payload=json.dumps({"presence" : "offline"}),
    qos=1,
    retain=True)

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[INFO] Voix {config['client_id_vox']} Connected with result code {reason_code}")
    if reason_code == 0:
        print("[INFO] Voix Connected")
        client.subscribe(config["TOPICS"]["mode_nuit_status"], qos=1)
        client.subscribe(config["TOPICS"]["led_status"], qos=1)
    else:
        print(f"[ERROR] Voix Connection failed with code {reason_code} {properties}")
        exit(1)

def on_message(client, userdata, msg):
    classification = client_utils.classify_kind(msg.topic)
    # print(f"[MSG] raw_message={msg.payload} classification={classification}")
    payload = msg.payload.decode("utf-8", errors="replace")
    data = json.loads(payload)
    print(
        f"[MSG] topic={msg.topic} "
        f"qos={msg.qos} retain={msg.retain} "
        f"payload={payload}")
    if "etat" in msg.topic:
        if data["state"] == "ON":
            led_status = True
        elif data["state"] == "OFF":
            led_status = False
    if "mode_nuit/state" in msg.topic:
        if data["state"] == "ON":
            mode_nuit_status = True
        elif data["state"] == "OFF":
            mode_nuit_status = False

    handlers = {
        # status handlers
        "led-state": handle_led_status,
        "nuit-state": handle_mode_nuit_status,
    }
    if classification in handlers:
        handlers[classification](client, data, payload)
    elif msg.topic != config["TOPICS"]["temperature"]:
        db_utils.insert_event(payload, topic=config["TOPICS"]["other"])

def handle_led_status(client, data, payload):
    global led_state
    if (data["state"]).strip().upper() == "ON":
        led_state = msg_led_on
    elif (data["state"]).strip().upper() == "OFF":
        led_state = msg_led_off
    else:
        led_state = "Le statut de la lampe est inconnue"

def handle_mode_nuit_status(client, data, payload):
    global mode_nuit_state
    if (data["state"]).strip().upper() == "ON":
        mode_nuit_state = msg_mode_nuit_on
    elif (data["state"]).strip().upper() == "OFF":
        mode_nuit_state = msg_mode_nuit_off
    else:
        mode_nuit_state = "Le statut de la mode nuit est inconnu"

client.on_connect = on_connect
client.on_disconnect = client_utils.on_disconnect
client.on_message = on_message
client.username_pw_set(username=config["user"], password=config["password"])
client.connect(config["BROKER_HOST"], config["BROKER_PORT"], keepalive=config["KEEPALIVE_SECONDS"])

print("[INFO] Connected")
print("[INFO] Waiting for messages")

client.loop_start()

result = client.publish(
    topic=config["TOPICS"]["presence_voix"],
    payload = json.dumps({"presence" : "online"}),
    qos=1,
    retain=True)

result.wait_for_publish()

try:
    mic, r = init_mic()
    while True:
        try:
            print("wait for hotword")
            if wait_for_hotword():
                print("hotword detected")
                respond("ecoute")
                topic, command = wait_for_command()
                print(f"[MSG] topic: {topic} command: {command}")

                if command is not None and topic is not None:
                    payload = {"state": command}
                    client.publish(
                        topic=topic,
                        payload=json.dumps(payload),  # dict Python -> string JSON
                        qos=1,
                        retain=False)
                    # db_utils.insert_measurement(json.dumps(payload), topic=topic)
                    # print(f"[PUB] {config["TOPICS"]["command_voix"]} -> {payload}")
            else:
                continue
        except Exception as e:
            print(f"[ERROR] {e}")
            continue


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


# if __name__ == "__main__":
#
#
#     listen()


    # voix_normalise("allume la lampe éteins la lampe fais clignoter la lampe donne-moi l’état active le mode nuit"))

    # respond("speak", "Bonjour, je suis la voix de ma maison")
