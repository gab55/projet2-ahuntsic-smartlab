import subprocess
import os
from unittest import result
import sys
import yaml
with open("../config.yaml", 'r') as ymlfile:
    config = yaml.load(ymlfile)
line = ""
for i in range(20):
    line = line + "~"

def run_cmd(cmd, check=True, stdout=None):
    """run a command with error handling"""
    try:
        subprocess.run(cmd, check=check, shell=True, stdout=stdout)
        if stdout:
            print(stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running command {cmd} : {e}")
        sys.exit(e.returncode)

def install_md() -> None:
    """install and setup mariadb broker"""
    print("installing mdb")
    run_cmd("apt update")
    run_cmd("apt install -y mariadb-server", stdout=True)

    print("starting mdb")
    run_cmd("systemctl enable --now mariadb", stdout=True)

    print("checking status:")
    run_cmd("systemctl status mariadb --no-pager", stdout=True)

    run_cmd("mariadb")
    run_cmd(f"CREATE USER {config("user")}@{config("BROKER_HOST")} IDENTIFIED BY {config("password")}")
    run_cmd(f"GRANT ALL PRIVILEGES ON {config("database")}.* TO {config("BROKER_HOST")};")
    run_cmd("FLUSH PRIVILEGES;", stdout=True)
    print(line)


def install_mosquitto() -> None:
    """install and setup mosquitto broker"""
    print("installing mosquitto")
    run_cmd("apt install -y mosquitto mosquitto-clients", stdout=True)
    run_cmd("sudo systemctl enable --now mosquitto", stdout=True)
    print("checking status:")
    run_cmd("systemctl status mosquitto --no-pager", stdout=True)
    print("checking ports: ")
    run_cmd("sudo ss -lntp | grep 1883", stdout=True)
    print("IP local")
    run_cmd("hostname -I")
    print(line)


# apres tester persistance:
#
# publish:
#     mosquitto_pub -h localhost -t 'test/hello' -m 'Bonjour MQTT'
#
# subscribe:
#     mosquitto_pub -h localhost -t 'test/retained' -m 'DERNIERE_VALEUR' -r
#
# fermer subscriber et relancer:
#     mosquitto_sub -h localhost -t 'test/retained' -v
#
# effacer un retained:
#     mosquitto_pub -h localhost -t 'test/retained' -r -n



def setup_venv():
    """setup virtualenv for project"""
    print("setting up venv")
    run_cmd("cd /home/gab/.git/Projet-1-Ahuntsic-SmartLab")
    run_cmd("python3 -m venv .venv")
    run_cmd("source .venv/bin/activate")
    run_cmd("which python", stdout=True)
    run_cmd("python --version", stdout=True)
    run_cmd("pip3 install -r requirements.txt", stdout=True)




pip install pymysql


def main():

    install_md()
    install_mosquitto()



if __name__ == "__main__":
    install_mdb()