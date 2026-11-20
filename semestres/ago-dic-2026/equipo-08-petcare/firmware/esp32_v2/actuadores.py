"""Una salida por GPIO. El servo conserva PWM hasta la parada explicita."""

import time
import config
from machine import Pin, PWM, Timer


class ServoSG90:
    def __init__(self, pin=config.PIN_SERVO):
        self.pin = Pin(pin, Pin.OUT, value=0)
        self.pwm = None
        self.pulse = None

    def move_us(self, pulse):
        if type(pulse) is not int or pulse not in (config.SERVO_OPEN_US, config.SERVO_CLOSED_US):
            raise ValueError("Solo se admiten los dos pulsos acordados")
        if self.pwm is None:
            # Esta compilacion de ESP32 requiere activar PWM con duty_u16 primero.
            self.pwm = PWM(self.pin, freq=50, duty_u16=(pulse * 65535 + 10000) // 20000)
            self.pwm.duty_ns(pulse * 1000)
        else:
            if self.pwm.freq() != 50:
                raise RuntimeError("La frecuencia del servo cambio; no enviar otro pulso")
            self.pwm.duty_ns(pulse * 1000)
        self.pulse = pulse

    def release(self):
        if self.pwm is not None:
            self.pwm.deinit()
        self.pwm = None
        self.pulse = None
        self.pin.value(0)

    def verify(self):
        if self.pwm is not None and self.pwm.freq() != 50:
            raise RuntimeError("Conflicto PWM del servo")


class PumpRelay:
    def __init__(self, pin=config.PIN_PUMP_RELAY):
        self.off_level = 1 - config.PUMP_ACTIVE_LEVEL
        self.pin = Pin(pin, Pin.OUT, value=self.off_level)
        self.timer = Timer(0)
        self.active = False
        self.until = None

    def _cutoff(self, timer):
        self.pin.value(self.off_level)
        self.active = False

    def on(self, duration_ms=5000):
        if type(duration_ms) is not int or not 1 <= duration_ms <= config.PUMP_PULSE_MS:
            raise ValueError("Agua: maximo 5000 ms")
        self.off()
        try:
            self.until = time.ticks_add(time.ticks_ms(), duration_ms)
            self.timer.init(period=duration_ms, mode=Timer.ONE_SHOT, callback=self._cutoff)
            self.pin.value(config.PUMP_ACTIVE_LEVEL)
            self.active = True
        except Exception:
            self.off()
            raise

    def tick(self, now):
        if self.until is not None and time.ticks_diff(now, self.until) >= 0:
            self.off()

    def off(self):
        self.pin.value(self.off_level)
        self.active = False
        self.until = None
        self.timer.deinit()


class ActiveBuzzer:
    def __init__(self, pin=config.PIN_BUZZER):
        self.pin = Pin(pin, Pin.OUT, value=1 - config.BUZZER_ACTIVE_LEVEL)
        self.pwm = None
        self.until = None
        self.started = None
        self.note = None

    def on(self, duration_ms=1000, mode=None):
        if type(duration_ms) is not int or not 100 <= duration_ms <= 2000:
            raise ValueError("Buzzer: duracion entre 100 y 2000 ms")
        mode = mode or config.BUZZER_MODE
        if mode not in ("active", "passive"):
            raise ValueError("Modo de buzzer desconocido")
        self.off()
        if mode == "active":
            self.pin.value(config.BUZZER_ACTIVE_LEVEL)
        elif mode == "passive":
            self.pwm = PWM(self.pin, freq=1000, duty_u16=32768)
            self.started = time.ticks_ms()
            self.note = 1000
        else:
            raise ValueError("Modo de buzzer desconocido")
        self.until = time.ticks_add(time.ticks_ms(), duration_ms)

    def tick(self, now):
        if self.until is not None and time.ticks_diff(now, self.until) >= 0:
            self.off()
        elif self.pwm is not None and self.started is not None:
            elapsed = time.ticks_diff(now, self.started)
            note = 1000 if elapsed < 700 else 0 if elapsed < 900 else 1500 if elapsed < 1700 else 0
            if note != self.note:
                if note:
                    self.pwm.freq(note)
                self.pwm.duty_u16(32768 if note else 0)
                self.note = note

    def off(self):
        if self.pwm is not None:
            self.pwm.deinit()
        self.pwm = None
        self.pin.value(1 - config.BUZZER_ACTIVE_LEVEL)
        self.until = None
        self.started = self.note = None
