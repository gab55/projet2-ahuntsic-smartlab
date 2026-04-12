import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main_utils
try:
    import RPi.GPIO as GPIO
    from gpiozero import CPUTemperature, LED
    mock = False
    print("GPIO Init OK")
except ImportError:
    import Mock.GPIO as GPIO
    from random import randint
    mock = True
    print("Mock GPIO Init")

GPIO.setmode(GPIO.BCM)

config = main_utils.get_config()

def gpio_init():
    """
    initialise les GPIO entre un GPIO ou un GPIO simule

    """
    if mock:
        return None
    else:
        GPIO.setmode(GPIO.BCM)
        return None


class Led:
    def __init__(self, pin):
        self.blink_state = False
        self.pin = pin
        self.state = False
        GPIO.setup(pin, GPIO.OUT)
        self.led = LED(self.pin)

    def led_on(self):
        """
        Allume le LED
        :return: None
        """
        if mock:
            print("Mock led on")
        else:
            if self.blink_state:
                self.blink_state = False
            GPIO.output(self.pin, GPIO.HIGH)
            self.state = True


    def led_off(self):
        """
        Ferme le LED et nettoie les ressources
        :return: None
        """
        if mock:
            print("Mock led off")
        else:
            if self.blink_state:
                self.blink_state = False
            GPIO.output(self.pin, GPIO.LOW)
            self.state = False

    def led_toggle(self):
        if self.state:
            self.led_off()
        else:
            self.led_on()
        return self.state

    def led_blink(self, duration=0.5):
        self.blink_state = not self.blink_state
        if mock:
            print("Mock led blink")
        else:
            if self.blink_state:
                self.led.blink(on_time=duration/2, off_time=duration/2)
            else:
                self.led_off()




def led_exit():
    """
    cleanups GPIO resources
    """
    if not mock:
        try:
            GPIO.cleanup()
        except RuntimeError:
            print("Error cleanup GPIO")

def cpu_temp():
    """
    Donne la temperature du CPU en Celsius
    :return: CPU temperature in C or randint(10, 30) when mock
    """
    if mock:
        return randint(10, 30)
    else:
        return CPUTemperature().temperature

def cpu_value():
    """
    Donne la temperature du CPU en value
    :return: CPU temperature value or randint(10, 30) when mock
    """
    if mock:
        return randint(10, 30)
    else:
        return CPUTemperature().value


if __name__ == "__main__":
    gpio_init()
    led = Led(config["LED_PIN"])
    try:
        while True:
            try:
                print(f'{time.strftime("%H:%M:%S")} la temperature est {cpu_temp()} °C', end=" ")
                led.led_on()
                time.sleep(1)
            finally:
                print(f'{time.strftime("%H:%M:%S")} la temperature est {cpu_temp()} °C', end=" ")
                led.led_off()
                time.sleep(1)
    finally:
        led.led_off()

