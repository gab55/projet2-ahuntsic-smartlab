import re
import subprocess
import unicodedata
from random import random

from french_lefff_lemmatizer.french_lefff_lemmatizer import FrenchLefffLemmatizer

from publisher_voix import voix_normalise




print(voix_normalise("allume la lampe éteins la lampe fais clignoter la lampe donne-moi l’état active le mode nuit"))

import json
import os
import random
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
import re
import nltk
from french_lefff_lemmatizer.french_lefff_lemmatizer import FrenchLefffLemmatizer
import speech_recognition as sr
import paho.mqtt.client as mqtt
import client_utils
import src.gpio as gpio
import main_utils
from db import db_utils
config = main_utils.get_config()
BROKER_HOST = config["BROKER_HOST"]
BROKER_PORT = config["BROKER_PORT_LOCAL"]
MIC_INDEX = 1
HOTWORD = "raspi"

TOPIC = "maison/voix"
rec_liste = {
    "oui": ["./aiff/aff.aiff"],#"Oui"
    "non": ["./aiff/aff.neg"],#"Non"
    "ecoute": ["./aiff/ecoute.neg", "./aiff/ecoute2.aiff"], #"Je vous écoute" "Oui?"
    "on": ["./aiff/lampon.aiff", "./aiff/lampon2.aiff","./aiff/lampon3.aiff"],# "Lampe allumée"#"J'ai allumée la lampe"
    "off": ["./aiff/lampoff.aiff", "./aiff/lampoff2.aiff", "./aiff/lampoff3.aiff"],# "J'ai éteint la lampe" "La lampe est éteint" "lampe éteint"
    "nuit_on": ["./aiff/nuiton.aiff"],#"J'ai activé la mode nuit"
    "nuit_off": ["./aiff/nuitoff.aiff"],#"J'ai desactivé la mode nuit"
    "cling": ["./aiff/cling.aiff"],#"Je clignote la lampe"
    "error": ["./aiff/error.aiff", "./aiff/error2.aiff","./aiff/error3.aiff"]}#"Je ne comprends pas"# Veuillez repeter"#"Je n'ai pas compris"#"Répétez, s'il vous plaît"

def detect_hotword(text):
    if HOTWORD in text:
        return True
    return None

def speak(text, lang="fr", speed=150):
    subprocess.run(["espeak-ng", "-v", lang, "-s", str(speed), text])

def play(file):
    if not os.path.exists(file):
        print(f"File {file} not found")
        return
    subprocess.run(["aplay", file])

def respond(category, text=""):
    if category in rec_liste:
        play(random.choice(rec_liste[category]))
    elif text != "":
        speak(text)
    else:
        play(random.choice(rec_liste["error"]))