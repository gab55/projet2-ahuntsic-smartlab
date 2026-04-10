import json
import time

def classify_kind(topic: str) -> str:
    """
    Classe l'événement selon le topic.
    """
    if "cmd" in topic:
        return "cmd"
    if "/state" in topic:
        return "state" # led state
    if "/status/" in topic:
        return "status" # presence
    if "etat" in topic:
        return "etat"
    if "nuit" in topic:
        return "nuit"
    if "cling" in topic:
        return "cling"

    return "other"

def is_telemetry(topic: str) -> bool:
    if "/sensors/" not in topic:
        return False
    if topic.endswith("/value"):
        return False
    return True


def parse_json(json_str: str):
    """
    parse json string into dict
    :param json_str:
    :return:
    """
    try:
        data = json.loads(json_str)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError as e:
        return False

def on_disconnect(client, userdata, reason_code, properties=None, *args):
    print(f"[DISCONNECT] reason_code={reason_code}")
    if reason_code != 0:
        reconnect(client)

def reconnect(client):
    retries = 0
    while retries < 5:
        try:
            client.reconnect()
            return
        except Exception as e:
            retries += 1
        print(f"[ERROR] Reconnection failed. Retrying... {retries}")
        time.sleep(2)
    print("[ERROR] Max retries reached. Exiting.")


if __name__ == "__main__":
    parse_json('{"test": "test"}')