# prend data sensor
# format data en json approprie
# conecte au broker
# publish
import json
import os
import time
import sys
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main_utils
import db.db_utils as db_utils
from gpio import cpu_temp
import client_utils

config = main_utils.get_config()

# Configuration Settings

client = mqtt.Client(
    client_id=config["client_id_pub"],
    callback_api_version = mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(username=config["user"], password=config["password"])

client.will_set(
    topic=config["TOPICS"]["presence"],
    payload=json.dumps({"presence" : "offline"}),
    qos=1,
    retain=True)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[INFO]{config['client_id_pub']} Connected")
    else:
        print(f"[ERROR] Connection failed with code {rc}")
        exit(1)

client.on_connect = on_connect
client.on_disconnect = client_utils.on_disconnect

client.connect(host=config["BROKER_HOST"], port=config["BROKER_PORT_LOCAL"], keepalive=config["KEEPALIVE_SECONDS"])

client.loop_start()
result = client.publish(
    topic=config["TOPICS"]["presence"],
    payload = json.dumps({"presence" : "online"}),
    qos=1,
    retain=True)

result.wait_for_publish()

try:

    while True:
        temperature_c = cpu_temp()
        db_utils.db_conn()
        payload = {
            "device": config["device_id"],
            "sensor": "temperature",
            "value": temperature_c,  # valeur numerique
            "unit": "C",  # unite
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}

        # Publication de la mesure
        topic = config["TOPICS"]["temperature"]
        client.publish(
            topic=topic,
            payload=json.dumps(payload),  # dict Python -> string JSON
            qos=0,
            retain=False)
        # db_utils.insert_measurement(json.dumps(payload), topic=topic)
        print(f"[PUB] {config["TOPICS"]["temperature"]} -> {payload}")

        time.sleep(config["measure_interval"])

except KeyboardInterrupt:
    print("\n[STOP] publisher arrêt demande")
finally:
    try:
        result = client.publish(
            topic=config["TOPICS"]["presence"],
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

