# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: controlador.py
# Objetivo: Coordinar la FSM de alimento/agua y sus bloqueos.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare - maquina de estados para servir alimento y activar la bomba.
# El ciclo principal no usa esperas largas: Thonny puede interrumpirlo con Stop.
import time
import config


class PetCareController:
    IDLE = "LISTO"
    FEED_OPEN = "COMPUERTA_ABIERTA"
    FEED_CLOSE = "COMPUERTA_CERRANDO"
    PUMPING = "BOMBA_ACTIVA"

    def __init__(self, sensors, servo, pump, buzzer, led):
        self.sensors = sensors
        self.servo = servo
        self.pump = pump
        self.buzzer = buzzer
        self.led = led
        self.state = self.IDLE
        self.deadline = 0
        self.status = {}
        self.last_event = "Sistema iniciado en modo seguro"
        self._last_beep_until = None
        self._signal_until = None

    def request_signal(self, now_ms):
        # Indicador breve de IA. No mueve la compuerta ni enciende la bomba.
        self._signal_until = self._add(now_ms, 1500)
        self.led.set_color('white')
        self.last_event = 'IA: perro confirmado; orden RGB blanca durante 1500 ms'
        return True, self.last_event

    @staticmethod
    def _diff(a, b):
        try:
            return time.ticks_diff(a, b)
        except AttributeError:
            return a - b

    @staticmethod
    def _add(a, delta):
        try:
            return time.ticks_add(a, delta)
        except AttributeError:
            return a + delta

    def request_feed(self, now_ms):
        if self.state != self.IDLE:
            return False, "Espera a que termine la accion actual"
        if not self.status.get("calibrated") or self.status.get("weight_g") is None:
            return False, "Calibra HX711 y completa config.py antes de dispensar"
        if self.status["weight_g"] >= config.BOWL_MAX_WEIGHT_G:
            self.last_event = "Dispensado bloqueado: el plato ya tiene suficiente peso"
            return False, self.last_event
        try:
            self.servo.move_to(config.SERVO_OPEN_ANGLE)
        except Exception as exc:
            self.last_event = "Error al activar servo: " + str(exc)
            return False, self.last_event
        self.state = self.FEED_OPEN
        self.deadline = self._add(now_ms, config.SERVO_OPEN_TIME_MS)
        self.last_event = "Compuerta de alimento abierta por tiempo limitado"
        return True, self.last_event

    def request_pump(self, now_ms):
        if self.state != self.IDLE:
            return False, "Espera a que termine la accion actual"
        if not self.status.get("water_available"):
            self.last_event = "Bomba bloqueada: flotador indica poca o nada de agua"
            return False, self.last_event
        try:
            self.pump.on()
        except Exception as exc:
            self.last_event = "Error al activar bomba: " + str(exc)
            return False, self.last_event
        duration = min(config.PUMP_PULSE_MS, config.PUMP_MAX_ON_MS)
        self.state = self.PUMPING
        self.deadline = self._add(now_ms, duration)
        self.last_event = "Bomba activa por pulso breve; revisa visualmente el plato"
        return True, self.last_event

    def stop_pump(self):
        self.pump.off()
        if self.state == self.PUMPING:
            self.state = self.IDLE
            self.last_event = "Bomba detenida manualmente"

    def tick(self, now_ms):
        try:
            self.status = self.sensors.read(now_ms)
        except Exception as exc:
            self.status = {"sensor_error": str(exc), "water_available": False, "calibrated": False}
            self.last_event = "Error de lectura de sensores: " + str(exc)
            self.pump.off()

        if self.state == self.FEED_OPEN and self._diff(now_ms, self.deadline) >= 0:
            try:
                self.servo.move_to(config.SERVO_CLOSED_ANGLE)
                self.state = self.FEED_CLOSE
                self.deadline = self._add(now_ms, config.SERVO_SETTLE_MS)
                self.last_event = "Compuerta cerrada; estabilizando servo"
            except Exception as exc:
                self.servo.release()
                self.state = self.IDLE
                self.last_event = "No se pudo cerrar la compuerta: " + str(exc)

        elif self.state == self.FEED_CLOSE and self._diff(now_ms, self.deadline) >= 0:
            self.servo.release()
            self.state = self.IDLE
            self.last_event = "Racion terminada; servo sin PWM en reposo"
            self.buzzer.on()
            self._last_beep_until = self._add(now_ms, 100)

        elif self.state == self.PUMPING:
            if not self.status.get("water_available"):
                self.pump.off()
                self.state = self.IDLE
                self.last_event = "Bomba detenida: flotador detecto nivel bajo"
            elif self._diff(now_ms, self.deadline) >= 0:
                self.pump.off()
                self.state = self.IDLE
                self.last_event = "Pulso de bomba terminado automaticamente"

        if self._last_beep_until is not None and self._diff(now_ms, self._last_beep_until) >= 0:
            self.buzzer.off()
            self._last_beep_until = None
        if self._signal_until is not None and self._diff(now_ms, self._signal_until) >= 0:
            self._signal_until = None
        self._update_led()
        return self.status

    def _update_led(self):
        if self._signal_until is not None:
            color = 'white'
        elif not self.status.get("water_available"):
            color = "red"
        elif not self.status.get("calibrated"):
            color = "yellow"
        elif self.status.get("pir"):
            color = "blue"
        else:
            color = "green"
        self.led.set_color(color)

    def snapshot(self):
        data = dict(self.status)
        data["state"] = self.state
        data["last_event"] = self.last_event
        data['ia_signal_active'] = self._signal_until is not None
        return data

    def safe_shutdown(self):
        self._signal_until = None
        self.pump.off()
        self.buzzer.off()
        try:
            if self.state == self.FEED_OPEN:
                self.servo.move_to(config.SERVO_CLOSED_ANGLE)
                time.sleep_ms(config.SERVO_SETTLE_MS)
        except Exception:
            pass
        self.servo.release()
        self.led.set_color("off")
        self.state = self.IDLE
