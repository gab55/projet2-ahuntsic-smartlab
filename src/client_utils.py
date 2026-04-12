import json
import time

def classify_kind(topic: str) -> str:
    """
    Classe l'événement selon le topic.
    """
    if "led" in topic:
        if "cmd" in topic:
            return "led-cmd"
        elif "state" in topic:
            return "led-state" # led state
        elif "cling" in topic:
            return "led-cling"
    if "nuit" in topic:
        if "cmd" in topic:
            return "nuit-cmd"
        elif "state" in topic:
            return "nuit-state"
    if "/status/" in topic:
        if "online" in topic:
            return "presence"
        elif "voix" in topic:
            return "presence_voix"
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
        return None

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None, *args):
    print(f"[DISCONNECT] disconnect_flags: {disconnect_flags}  reason_code: {reason_code}")
    if disconnect_flags.is_disconnect_packet_from_server:
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