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
led_state = False
mode_nuit_state = False

led = gpio.Led(config['led'])
mode_nuit = gpio.Led(config['led_mode_nuit'])

client = mqtt.Client(client_id=config["client_id_sub"],
                     callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[CONNECT] reason_code={reason_code}")
    gpio.gpio_init()
    if reason_code == 0:
        client.subscribe(config["TOPICS"]["temperature"], qos=0)

        client.subscribe(config["TOPICS"]["presence"], qos=1)
        client.subscribe(config["TOPICS"]["presence_voix"], qos=1)

        client.subscribe(config["TOPICS"]["led_command"], qos=1)
        client.subscribe(config["TOPICS"]["mode_nuit"], qos=1)
        client.subscribe(config["TOPICS"]["led_cling"], qos=1)

        client.subscribe(config["TOPICS"]["led_status"], qos=1)
        client.subscribe(config["TOPICS"]["mode_nuit_status"], qos=1)
        client.subscribe(config["TOPICS"]["other"], qos=1)


    else:
        print("[ERROR] Connexion refusée ou échouée. Verifier Mosquitto, host, port, auth.")
        exit(1)

def on_message(client, userdata, msg):
    classification = client_utils.classify_kind(msg.topic)
    payload = msg.payload.decode("utf-8", errors="replace")
    print(
        f"[MSG] topic={msg.topic} "
        f"qos={msg.qos} retain={msg.retain} "
        f"payload={payload}"
    )

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        data = {"state": payload}

    # handle temperature readings
    if client_utils.is_telemetry(msg.topic):
        db_utils.insert_measurement(payload, topic=msg.topic)

    elif not client_utils.is_telemetry(msg.topic):
        handlers = {
            # command handlers
            "nuit-cmd": handle_mode_nuit,
            "led-cmd": handle_led_command,
            "led-cling": handle_cling,

            # presence handlers
            "presence": handle_presence,
            "presence_voix": handle_presence_voix,

            # status handlers
            "led-state": handle_led_status,
            "nuit-state": handle_mode_nuit_status,

            # other handlers
            "other": handle_error,
        }
        if classification in handlers:
            handlers[classification](client, data, payload)
        elif msg.topic != config["TOPICS"]["temperature"]:
            db_utils.insert_event(payload, topic=config["TOPICS"]["other"])


def handle_presence(client, data, payload):
    db_utils.insert_event(payload, topic=config["TOPICS"]["presence"])

def handle_presence_voix(client, data, payload):
    db_utils.insert_event(payload, topic=config["TOPICS"]["presence_voix"])

def handle_mode_nuit(client, data, payload):
    cmd = (data["state"]).strip().upper()
    if cmd in ["ON", "OFF"]:
        if cmd == "ON":
            mode_nuit.led_on()
            print("led on")
            state = "ON"
        elif cmd == "OFF":
            mode_nuit.led_off()
            print("led off")
            state = "OFF"
        payload = {"state": state}

        client.publish(config["TOPICS"]["mode_nuit_status"], json.dumps(payload), qos=1, retain=True)
        log_event(config["device_id"], "mode_nuit", state, config["TOPICS"]["mode_nuit"])
    else:
        print("[error] mode nuit must be ON or OFF")

def handle_led_command(client, data, payload):
    cmd = (data["state"]).strip().upper()
    if cmd in ["ON", "OFF"]:
        if cmd == "ON":
            led.led_on()
            print("led on")
            state = "ON"
        elif cmd == "OFF":
            led.led_off()
            print("led off")
            state = "OFF"
        payload = {"state": state}

        client.publish(config["TOPICS"]["led_status"], json.dumps(payload), qos=1, retain=True)
        log_event(config["device_id"], f"mode nuit", state, config["TOPICS"]["led_command"])
    else:
        print("[error] led must be ON or OFF")

def handle_led_status(client, data, payload):
    db_utils.insert_event(payload, topic=config["TOPICS"]["led_status"])

def handle_mode_nuit_status(client, data, payload):
    db_utils.insert_event(payload, topic=config["TOPICS"]["mode_nuit_status"])

def handle_error(client, data, payload):
    print("[ERROR] ", payload)

def handle_cling(client, data, payload):
    led.led_blink()
    cmd = "blink on" if led.blink_state else "blink off"
    print(f"cling {cmd}")
    log_event(config["device_id"], f"lampe_blink", cmd, config["TOPICS"]["other"])

def log_event(device, actuator, state, topic):
    payload = {
        "device": device,
        "actuator": actuator,
        "state": state,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    }
    db_utils.insert_event(payload, topic=topic)

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
