# prendre data capteur
# creer des json formated
# envoyer avec mqtt publisher
import json
import signal
import subprocess

import yaml

with open("config.yaml", 'r') as file:
    config = yaml.safe_load(file)
    if config is None:
        raise ValueError("config.yaml is empty")

import db.db_utils as db_utils



def requirements():
    """
    check if mosquitto and mariadb are running and requirements are installed
    :return:
    """
    #subprocess.run(["pip3", "install", "-r", "requirements.txt"])
    mosquitto = subprocess.run(["sudo", "systemctl", "is-active", "mosquitto"], capture_output=True, text=True, check=True)
    print(f'Mosquitto : {mosquitto.stdout}')
    if mosquitto.stdout != "active\n":
        subprocess.run(["sudo", "systemctl", "start", "mosquitto"])

    mariadb = subprocess.run(["sudo", "systemctl", "is-active", "mariadb"], capture_output=True, text=True, check=True)
    print(f'MariaDB : {mariadb.stdout}')
    if mariadb.stdout != "active\n":
        subprocess.run(["sudo", "systemctl", "start", "mariadb"])


def main():
    subscriber_process = subprocess.Popen([
        "python3",
        "src/publisher_sensor.py"])

    print("publisher_sensor started")

    publisher_process = subprocess.Popen([
        "python3",
        "src/subscriber_led.py"])

    print("subscriber_led started")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Quitting processes")

        publisher_process.send_signal(signal.SIGINT)
        publisher_process.wait(timeout=5)


        subscriber_process.send_signal(signal.SIGINT)
        subscriber_process.wait(timeout=5)
        db_utils.insert_event(json.dumps({"presence" : "offline"}), topic=config["TOPICS"]["presence"])

if __name__ == "__main__":
    db_utils.db_create()
    main()


