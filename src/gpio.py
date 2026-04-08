import time
import yaml

try:
    import RPi.GPIO as GPIO
    from gpiozero import CPUTemperature
    mock = False
    print("GPIO Init OK")
except ImportError:
    import Mock.GPIO as GPIO
    from random import randint
    mock = True
    print("Mock GPIO Init")

GPIO.setmode(GPIO.BCM)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def gpio_init():
    if mock:
        return None
    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config['led'], GPIO.OUT)

def led_on():
    """
    Allume le LED
    :return: None
    """
    if mock:
        print("Mock led on")
    else:
        GPIO.output(config['led'], GPIO.HIGH)


def led_off():
    """
    Ferme le LED et nettoie les ressources
    :return: None
    """
    if mock:
        print("Mock led off")
    else:
        GPIO.output(config['led'], GPIO.LOW)

def led_exit():
    if not mock:
        try:
            GPIO.cleanup()
        except RuntimeError:
            print("Error cleanup GPIO")

def cpu_temp():
    """
    Donne la temperature du CPU en Celsius
    :return: CPU temperature or randint(10, 30) when mock
    """
    if mock:
        return randint(10, 30)
    else:
        return CPUTemperature().temperature

def cpu_value():
    """
    Donne la temperature du CPU en Celsius
    :return: CPU temperature or randint(10, 30) when mock
    """
    if mock:
        return randint(10, 30)
    else:
        return CPUTemperature().value


if __name__ == "__main__":
    try:
        while True:
            try:
                print(f'{time.strftime("%H:%M:%S")} la temperature est {cpu_temp()} °C', end=" ")
                led_on()
                time.sleep(1)
            finally:
                print(f'{time.strftime("%H:%M:%S")} la temperature est {cpu_temp()} °C', end=" ")
                led_off()
                time.sleep(1)
    finally:
        led_off()

