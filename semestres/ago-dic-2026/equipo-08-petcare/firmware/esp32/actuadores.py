# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: actuadores.py
# Objetivo: Encapsular servo posicional, bomba por MOSFET, buzzer y LED RGB.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare - salidas seguras y con tiempos limitados.
import config


# Nombre historico conservado para no romper imports; tambien usado con MG995.
class ServoSG90:
    def __init__(self, pin=config.PIN_SERVO):
        from machine import Pin
        self._pin = Pin(pin, Pin.OUT)
        self._pwm = None

    def move_to(self, angle):
        from machine import PWM
        angle = max(config.SERVO_MIN_ANGLE, min(config.SERVO_MAX_ANGLE, int(angle)))
        if self._pwm is None:
            self._pwm = PWM(self._pin, freq=50, duty_u16=0)
        angle_span = config.SERVO_MAX_ANGLE - config.SERVO_MIN_ANGLE
        if angle_span <= 0:
            raise ValueError("Revisa SERVO_MIN_ANGLE y SERVO_MAX_ANGLE")
        position = (angle - config.SERVO_MIN_ANGLE) / angle_span
        pulse_span = config.SERVO_MAX_PULSE_US - config.SERVO_MIN_PULSE_US
        pulse_us = config.SERVO_MIN_PULSE_US + (pulse_span * position)
        self._pwm.duty_ns(int(pulse_us * 1000))

    def release(self):
        # Sin PWM en reposo se evitan zumbidos y correcciones constantes del servo.
        if self._pwm is not None:
            try:
                self._pwm.deinit()
            finally:
                self._pwm = None
        self._pin.value(0)


class PumpMOSFET:
    def __init__(self, pin=config.PIN_PUMP_MOSFET):
        from machine import Pin
        self._pin = Pin(pin, Pin.OUT, value=0)
        self.off()

    def on(self):
        self._pin.value(1)

    def off(self):
        self._pin.value(0)


class ActiveBuzzer:
    def __init__(self, pin=config.PIN_BUZZER):
        from machine import Pin
        self._pin = Pin(pin, Pin.OUT, value=0)
        self.off()

    def on(self):
        self._pin.value(1)

    def off(self):
        self._pin.value(0)


class RGBLed:
    def __init__(self):
        from machine import Pin
        self._r = Pin(config.PIN_LED_R, Pin.OUT, value=0)
        self._g = Pin(config.PIN_LED_G, Pin.OUT, value=0)
        self._b = Pin(config.PIN_LED_B, Pin.OUT, value=0)

    def set_color(self, color):
        values = {
            "off": (0, 0, 0), "green": (0, 1, 0), "blue": (0, 0, 1),
            "yellow": (1, 1, 0), "red": (1, 0, 0), "white": (1, 1, 1),
        }
        r, g, b = values.get(color, values["off"])
        self._r.value(r)
        self._g.value(g)
        self._b.value(b)
