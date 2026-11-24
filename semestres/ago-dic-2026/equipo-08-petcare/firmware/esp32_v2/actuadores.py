"""Una salida por GPIO. El servo conserva PWM hasta la parada explicita."""
# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Controlar el MG995, el relevador y el buzzer desde GPIO seguros.

import time
import config
from machine import Pin, PWM, Timer


class ServoMG995:
    def __init__(self, pin=config.PIN_SERVO):
        self.pin = Pin(pin, Pin.OUT, value=0)
        self.pwm = None
        self.pulse = None

    def move_us(self, pulse):
        low = min(config.SERVO_OPEN_US, config.SERVO_CLOSED_US)
        high = max(config.SERVO_OPEN_US, config.SERVO_CLOSED_US)
        if type(pulse) is not int or not low <= pulse <= high:
            raise ValueError("Pulso del servo fuera del recorrido configurado")
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
        self.pattern = None

    def cue(self, kind):
        """Reproduce un aviso corto sin bloquear el control de motores."""
        if kind == "gate":
            # Dos tonos breves ascendentes, semejantes a un ladrido sintetico.
            pattern = ((0, 1250), (90, 0), (125, 1750), (225, 0), (270, 1450), (370, 0))
            duration_ms = 420
        elif kind == "water":
            # Tres notas ascendentes para distinguir el ciclo de agua.
            pattern = ((0, 880), (100, 0), (125, 1175), (225, 0), (250, 1568), (390, 0))
            duration_ms = 450
        else:
            raise ValueError("Aviso sonoro desconocido")
        self.off()
        if config.BUZZER_MODE == "active":
            self.pin.value(config.BUZZER_ACTIVE_LEVEL)
            self.started = time.ticks_ms()
            self.until = time.ticks_add(self.started, duration_ms)
            self.pattern = ((0, 1), (duration_ms, 0))
            self.note = None
            return
        self.pwm = PWM(self.pin, freq=pattern[0][1] or 1000, duty_u16=0)
        self.started = time.ticks_ms()
        self.until = time.ticks_add(self.started, duration_ms)
        self.pattern = pattern
        self.note = None
        self._apply_pattern(0)

    def _apply_pattern(self, elapsed):
        note = 0
        for offset, frequency in self.pattern:
            if elapsed < offset:
                break
            note = frequency
        if note != self.note:
            if self.pwm is not None:
                if note:
                    self.pwm.freq(note)
                self.pwm.duty_u16(32768 if note else 0)
            else:
                self.pin.value(config.BUZZER_ACTIVE_LEVEL if note else 1 - config.BUZZER_ACTIVE_LEVEL)
            self.note = note

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
            self.pattern = None
        else:
            raise ValueError("Modo de buzzer desconocido")
        self.until = time.ticks_add(time.ticks_ms(), duration_ms)

    def tick(self, now):
        if self.until is not None and time.ticks_diff(now, self.until) >= 0:
            self.off()
        elif self.pattern is not None and self.started is not None:
            self._apply_pattern(time.ticks_diff(now, self.started))
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
        self.pattern = None
