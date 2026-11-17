# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: actuadores.py
# Objetivo: Encapsular servo posicional, bomba por rele, buzzer y LED RGB.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo MG995=33, bomba rele=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare - salidas seguras y con tiempos limitados.
import config


# Nombre historico conservado para no romper imports; tambien usado con MG995.
class ServoSG90:
    def __init__(self, pin=config.PIN_SERVO):
        from machine import Pin
        self._pin = Pin(pin, Pin.OUT)
        self._pwm = None

    def move_us(self, pulse_us):
        from machine import PWM
        if isinstance(pulse_us, bool) or not isinstance(pulse_us, int):
            raise ValueError('El pulso debe ser un entero en microsegundos')
        if not config.SERVO_MIN_PULSE_US <= pulse_us <= config.SERVO_MAX_PULSE_US:
            raise ValueError('Pulso fuera del recorrido validado de la compuerta')
        if self._pwm is None:
            self._pwm = PWM(self._pin, freq=50, duty_ns=int(pulse_us * 1000))
        self._pwm.duty_ns(int(pulse_us * 1000))

    def release(self):
        # Solo en parada o error: el montaje puede moverse al retirar la senal.
        if self._pwm is not None:
            try:
                self._pwm.deinit()
            finally:
                self._pwm = None
        self._pin.value(0)


class PumpRelay:
    def __init__(self, pin=config.PIN_PUMP_RELAY):
        from machine import Pin, Timer
        self._off_level = 1 - config.PUMP_ACTIVE_LEVEL
        self._pin = Pin(pin, Pin.OUT, value=self._off_level)
        self.active = False
        self._timer = Timer(config.PUMP_TIMER_ID)

    def _cutoff(self, timer):
        # Respaldo del plazo de la FSM. En ESP32 el callback es soft.
        self._pin.value(self._off_level)
        self.active = False

    def on(self):
        self.off()
        from machine import Timer
        duration = min(15000, config.PUMP_PULSE_MS, config.PUMP_MAX_ON_MS)
        if duration <= 0:
            raise ValueError('Duracion de bomba invalida')
        try:
            self._timer.init(period=duration, mode=Timer.ONE_SHOT, callback=self._cutoff)
            self.active = True
            self._pin.value(config.PUMP_ACTIVE_LEVEL)
        except Exception:
            self.off()
            raise

    def off(self):
        self._pin.value(self._off_level)
        self.active = False
        self._timer.deinit()


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
