""" 
publisher_temperature.py 
Objectif: - Lire une mesure (capteur réel ou simulation) 
- Construire un message JSON (contrat de données) - Publier sur MQTT (Mosquitto) 
 
Contexte d'architecture: 
Raspberry Pi (publisher) -> Mosquitto (broker) -> MQTT Dash / autres clients 
(subscribers) 
""" 
 
from __future__ import annotations 
 
import json 
import random 
import time 
from datetime import datetime, timezone 
 
import paho.mqtt.client as mqtt 
 
# --------------------------------------------------------------------- 
# 1) Paramètres MQTT (adaptables par équipe) 
# --------------------------------------------------------------------- 
 
BROKER_HOST = "localhost"     # Sur le Pi: Mosquitto tourne localement 
BROKER_PORT = 1883            # Port MQTT classique 
KEEPALIVE_S = 60              # Ping/keepalive (secondes) 
 
CLIENT_ID = "b3-pub-pi01"     # Doit être unique sur le broker (sinon déconnexion de l'autre client) 
 
TEAM = "demo" 
DEVICE = "pi01" 
 
TOPIC_JSON = f"ahuntsic/aec-iot/b3/{TEAM}/{DEVICE}/sensors/temperature" 
TOPIC_VALUE = f"ahuntsic/aec-iot/b3/{TEAM}/{DEVICE}/sensors/temperature/value" 
 
# Statut "online/offline" pratique en IoT (peut être affiché aussi dans un dashboard) 
TOPIC_ONLINE = f"ahuntsic/aec-iot/b3/{TEAM}/{DEVICE}/status/online" 
 
# QoS: 
# - capteurs fréquents -> QoS 0 (rapide, pas d'ack) 
# - états/commandes -> souvent QoS 1 (plus fiable) 
QOS_SENSOR = 0 
QOS_STATUS = 1 
 
PUBLISH_PERIOD_S = 2.0 
 
# --------------------------------------------------------------------- 
# 2) Lecture capteur (à brancher sur VOTRE code du cours précédent) 
# --------------------------------------------------------------------- 
 
def read_temperature_c() -> float: 
    """ 
    Retourne une température en °C. 
    Remplace cette fonction par la lecture de ton capteur réel (bloc précédent). 
    Ici: simulation pour que tout le monde puisse avancer même sans matériel branché. 
    """ 
    return round(20.0 + random.random() * 5.0, 2) 
 
# --------------------------------------------------------------------- 
# 3) Callbacks MQTT (événementiel) 
# --------------------------------------------------------------------- 
 
connected = False  # drapeau simple pour savoir si on est connecté 
 
def on_connect(client, userdata, flags, reason_code, properties=None): 
    """ 
    Appelé quand le broker répond à la connexion. 
    - Si reason_code == 0 => connexion OK (MQTT v3.1.1) 
    """ 
    global connected 
    print(f"[CONNECT] reason_code={reason_code}") 
    connected = (reason_code == 0) 
 
def on_disconnect(client, userdata, reason_code, properties=None): 
    """ 
    Appelé quand la connexion tombe. 
    reason_code != 0 => déconnexion inattendue (réseau, broker down, etc.) 
    """ 
    global connected 
    print(f"[DISCONNECT] reason_code={reason_code}") 
    connected = False 
 
# --------------------------------------------------------------------- 
# 4) Création du client + LWT + connexion 
# --------------------------------------------------------------------- 
 
client = mqtt.Client( 
    client_id=CLIENT_ID,          # IMPORTANT: utiliser le paramètre nommé (évite confusion de versions) 
    protocol=mqtt.MQTTv311         # protocole courant (MQTT 3.1.1) 
) 
 
client.on_connect = on_connect 
client.on_disconnect = on_disconnect 
 
# LWT (Last Will): si le Pi meurt sans se déconnecter proprement, 
# le broker publiera "offline" sur TOPIC_ONLINE. 
client.will_set( 
    topic=TOPIC_ONLINE, 
    payload="offline", 
    qos=QOS_STATUS, 
    retain=True 
) 
 
# Option utile en IoT: délai de reconnexion progressif (évite spam réseau) 
# (On garde ça simple; on le renforcera dans les prochaines séances) 
client.reconnect_delay_set(min_delay=1, max_delay=30) 
 
# Connexion non bloquante + thread réseau: 
client.connect_async(BROKER_HOST, BROKER_PORT, keepalive=KEEPALIVE_S) 
client.loop_start() 
 
# --------------------------------------------------------------------- 
# 5) Boucle principale (capteur -> publish) 
# --------------------------------------------------------------------- 
 
try: 
    # Publie "online" au démarrage (retain=True = dernier état conservé) 
    client.publish(TOPIC_ONLINE, "online", qos=QOS_STATUS, retain=True) 
 
    while True: 
        if not connected: 
            # Si pas connecté, on attend un peu (la boucle réseau tente de reconnecter) 
            print("[WAIT] en attente de connexion MQTT...") 
            time.sleep(1.0) 
            continue 
 
        temperature_c = read_temperature_c() 
 
        payload = { 
            "device_id": DEVICE, 
            "sensor": "temperature", 
            "value": temperature_c, 
            "unit": "C", 
            "ts": datetime.now(timezone.utc).isoformat() 
        } 
 
        # 1) Message JSON (contrat "riche") 
        client.publish(TOPIC_JSON, json.dumps(payload), qos=QOS_SENSOR, retain=False) 
 
        # 2) Valeur simple (facile pour dashboards) 
        client.publish(TOPIC_VALUE, str(temperature_c), qos=QOS_SENSOR, retain=False) 
        print(f"[PUB] {TOPIC_JSON} -> {payload}") 
        time.sleep(PUBLISH_PERIOD_S) 
except KeyboardInterrupt: 
    print("\n[STOP] arrêt demandé (Ctrl+C)") 
finally: 
    # Arrêt propre: on publie offline "normal" 
    client.publish(TOPIC_ONLINE, "offline", qos=QOS_STATUS, retain=True) 
    client.loop_stop() 
    client.disconnect() 