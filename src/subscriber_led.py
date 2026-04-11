# Reçois les json du broker
# envoie command led / alume led
# publish state
#
import json
import sys
import os
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db.db_utils as db_utils
import paho.mqtt.client as mqtt
import signal
import gpio
import client_utils
config = main_utils.get_config()

led = gpio.Led(config['led'])
mode_nuit = gpio.Led(config['led_mode_nuit'])

client = mqtt.Client(client_id=config["client_id_sub"],
                     callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[CONNECT] reason_code={reason_code}")
    gpio.gpio_init()
    if reason_code == 0:
        client.subscribe(config["TOPICS"]["led_command"], qos=1)
        client.subscribe(config["TOPICS"]["presence"], qos=1)
        client.subscribe(config["TOPICS"]["led_status"], qos=1)
        client.subscribe(config["TOPICS"]["temperature"], qos=0)
        client.subscribe(config["TOPICS"]["presence_voix"], qos=1)
        client.subscribe(config["TOPICS"]["mode_nuit"], qos=1)

    else:
        print("[ERROR] Connexion refusée ou échouée. Verifier Mosquitto, host, port, auth.")
        exit(1)



# def command(payload, led, cmd):
#     print(f"[CMD] {payload}")
#     if cmd not in ["ON", "OFF"]:
#         raise ValueError("state must be ON or OFF")
#     elif cmd in ["ON"]:
#         led.led_on()
#         print("led on")
#         return "ON"
#     elif cmd in ["OFF"]:
#         led.led_off()
#         print("led off")
#         return "OFF"
#     else:
#         return "ERROR"



def on_message(client, userdata, msg):
    classification = client_utils.classify_kind(msg.topic)
    # print(f"[MSG] raw_message={msg.payload} classification={classification}")
    payload = msg.payload.decode("utf-8", errors="replace")

    print(
        f"[MSG] topic={msg.topic} "
        f"qos={msg.qos} retain={msg.retain} "
        f"payload={payload}")
    if client_utils.is_telemetry(msg.topic):
        db_utils.insert_measurement(payload, topic=msg.topic)
    cmd = payload.strip().upper()
    print(f"[CMD] {payload}")
    if classification == "cmd":
        if cmd in ["ON"]:
            led.led_on()
            print("led on")
            state = "ON"
        elif cmd in ["OFF"]:
            led.led_off()
            print("led off")
            state = "OFF"
        else:
            state = "ERROR"
        payload = {"state": cmd}
        client.publish(config["TOPICS"]["led_status"], json.dumps(payload), qos=1, retain=True)

        payload = {
            "device": config["device_id"],
            "actuator": f"led-{config['led']}",
            "state": f"{state}",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        db_utils.insert_event(json.dumps(payload), topic=config["TOPICS"]["led_command"])

    elif classification == "state":
        db_utils.insert_event(payload, topic=config["TOPICS"]["led_status"])
    elif classification == "status":
        db_utils.insert_event(payload, topic=config["TOPICS"]["presence"])
    elif classification == "etat":
        db_utils.insert_event(payload, topic=config["TOPICS"]["etat"])
    elif classification == "nuit":
        if cmd == "ON":
            mode_nuit.led_on()
            print("led on")
            state = "ON"
        elif cmd == "OFF":
            mode_nuit.led_off()
            print("led off")
            state = "OFF"
        else:
            state = "ERROR"
        payload = {"state": cmd}
        client.publish(config["TOPICS"]["mode_nuit_status"], json.dumps(payload), qos=1, retain=True)
        payload = {
            "device": config["device_id"],
            "actuator": f"mode_nuit",
            "state": f"{state}",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        db_utils.insert_event(json.dumps(payload), topic=config["TOPICS"]["mode_nuit"])

    elif classification == "cling":
        led.led_blink()
        if not led.blink_state:
            cmd = "blink off"
        else:
            cmd = "blink on"
        print(f"cling {cmd}")
        payload = {cmd}
        client.publish(config["TOPICS"]["mode_nuit_status"], json.dumps(payload), qos=1, retain=True)

        payload = {
            "device": config["device_id"],
            "actuator": f"mode_nuit",
            "state": f"{cmd}",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        db_utils.insert_event(json.dumps(payload), topic=config["TOPICS"]["led_status"])


    else:
        if msg.topic == config['TOPICS']['temperature']:
            return
        db_utils.insert_event(payload, topic=config["TOPICS"]["other"])


def signal_handler(signal, frame):
    print("Quitting Subscriber")
    client.loop_stop()
    client.disconnect()
    sys.exit(0)



client.on_connect = on_connect
client.on_disconnect = client_utils.on_disconnect
client.on_message = on_message
signal.signal(signal.SIGINT, signal_handler)
client.username_pw_set(username=config["user"], password=config["password"])
client.connect(config["BROKER_HOST"], config["BROKER_PORT"], keepalive=config["KEEPALIVE_SECONDS"])
print("[INFO] Connected")
print("[INFO] Waiting for messages")
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("[STOP] arret demande")
    gpio.led_exit()

print("[INFO] Disconnected")
