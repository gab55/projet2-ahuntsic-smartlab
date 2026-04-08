# Reçois les json du broker
# envoie command led / alume led
# publish state
#
import json
import sys
import os
from datetime import datetime, timezone
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db.db_utils as db_utils
import paho.mqtt.client as mqtt
import signal
import yaml
import gpio
import client_utils

with open("config.yaml", 'r') as file:
    config = yaml.safe_load(file)
    if config is None:
        raise ValueError("config.yaml is empty")



def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[CONNECT] reason_code={reason_code}")
    gpio.gpio_init()
    if reason_code == 0:
        client.subscribe(config["TOPICS"]["led_command"], qos=1)
        client.subscribe(config["TOPICS"]["presence"], qos=1)
        client.subscribe(config["TOPICS"]["led_status"], qos=1)
        client.subscribe(config["TOPICS"]["temperature"], qos=0)
    else:
        print("[ERROR] Connexion refusée ou échouée. Verifier Mosquitto, host, port, auth.")


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
    if classification == "cmd":
        cmd = payload.strip().upper()
        print(f"[CMD] {payload}")
        if cmd not in ["ON", "OFF"]:
            raise ValueError("state must be ON or OFF")
        elif cmd in ["ON"]:
            gpio.led_on()
            print("led on")
            state = "ON"
        elif cmd in ["OFF"]:
            gpio.led_off()
            print("led off")
            state = "OFF"
        else:
            state = "ERROR"
        payload = {"state": cmd}
        db_utils.insert_event(json.dumps(payload), topic=config["TOPICS"]["led_command"])
        payload = {
            "device": config["device_id"],
            "actuator": f"led-{config['led']}",
            "state": f"{state}",
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
        client.publish(config["TOPICS"]["led_status"], json.dumps(payload), qos=1, retain=True)
    elif classification == "state":
        db_utils.insert_event(payload, topic=config["TOPICS"]["led_status"])
    elif classification == "status":
        db_utils.insert_event(payload, topic=config["TOPICS"]["presence"])
    else:
        if msg.topic == config['TOPICS']['temperature']:
            return
        db_utils.insert_event(payload, topic=config["TOPICS"]["other"])


def signal_handler(signal, frame):
    print("Quitting Subscriber")
    client.loop_stop()
    client.disconnect()
    sys.exit(0)




client = mqtt.Client(client_id=config["client_id_sub"],
                     callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
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
