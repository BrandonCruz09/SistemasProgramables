# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: controlador.py
# Objetivo: Coordinar la FSM de alimento/agua y sus bloqueos.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo MG995=33, bomba rele=23, buzzer=22
# ============================================
# PetCare - maquina de estados para servir alimento y activar la bomba.
# El ciclo principal no usa esperas largas: Thonny puede interrumpirlo con Stop.
import time
import math
import config


class PetCareController:
    IDLE = "LISTO"
    FEED_OPEN = "COMPUERTA_ABIERTA"
    FEED_CLOSE = "COMPUERTA_CERRANDO"
    PUMPING = "BOMBA_ACTIVA"
    FAULT = "ERROR_ACTUADOR"

    def __init__(self, sensors, servo, pump, buzzer):
        self.sensors = sensors
        self.servo = servo
        self.pump = pump
        self.buzzer = buzzer
        self.state = self.IDLE
        self.deadline = 0
        self.status = {}
        self.last_event = "Sistema iniciado en modo seguro"
        self._last_beep_until = None
        self._signal_until = None
        self.water_events = []
        self._water_seq = 0
        try:
            import os
            import binascii
            self._boot_id = binascii.hexlify(os.urandom(8)).decode()
        except ImportError:
            self._boot_id = str(id(self))
        self._water_run = None
        self._pump_ready_at = None
        self._last_sensor_ms = None
        self.fault = None
        self.aux_errors = {}
        self.actions_allowed = True
        self.servo_holding = False
        self.gate_command = None
        self.food_target = None
        self.manual_food_started = None
        self.food_cycles = 0
        self.food_started = None
        self.food_weigh_at = None
        self.food_last_weight = None
        self.food_no_progress = 0
        self.food_result = 'Sin servido solicitado'

    def action_in_progress(self):
        return self.state in (self.FEED_OPEN, self.FEED_CLOSE, self.PUMPING)

    def _optional(self, name, action, *args):
        try:
            action(*args)
            self.aux_errors.pop(name, None)
        except Exception as exc:
            message = repr(exc)
            if self.aux_errors.get(name) != message:
                print(name, message)
            self.aux_errors[name] = message

    def _actuator_fault(self, message):
        self.food_target = None
        self.manual_food_started = None
        self.food_result = message
        self.fault = message
        self.last_event = message
        self.state = self.FAULT
        self._optional('bomba', self.pump.off)
        self._optional('servo', self.servo.release)
        self._optional('buzzer', self.buzzer.off)
        print(message)

    def _water_event(self, phase, now_ms, reason):
        run = self._water_run
        if run is None:
            return
        event = dict(run)
        event.update({'id': run['run_id'] + '-' + phase, 'phase': phase,
                      'uptime_ms': now_ms, 'reason': reason,
                      'duration_ms': max(0, self._diff(now_ms, run['started_ms'])),
                      'volume_ml': None, 'water_level_monitored': False,
                      'physical_flow_verified': False})
        self.water_events.append(event)

    def _finish_water(self, now_ms, reason):
        self.pump.off()
        self._water_event('finished', now_ms, reason)
        self._water_run = None
        self.state = self.IDLE
        self._pump_ready_at = self._add(now_ms, config.PUMP_COOLDOWN_MS)
        self.last_event = 'Agua: ' + reason

    def request_signal(self, now_ms):
        # Registra la deteccion; no activa componentes fisicos.
        self._signal_until = self._add(now_ms, 1500)
        self.last_event = 'IA: perro confirmado; evento registrado sin actuadores'
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

    def request_beep(self, now_ms, duration_ms=2000):
        if not self.actions_allowed or self.fault or self.state != self.IDLE:
            return False, 'Espera a que termine la accion actual'
        if not config.BUZZER_ENABLED:
            return False, 'Buzzer desactivado en configuracion'
        self._optional('buzzer', self.buzzer.on)
        if 'buzzer' in self.aux_errors:
            return False, 'No se pudo activar el buzzer'
        self._last_beep_until = self._add(now_ms, min(2000, max(100, duration_ms)))
        return True, 'Pulso de sonido enviado al buzzer'

    def request_gate(self, opened, now_ms):
        if not self.actions_allowed or self.fault:
            return False, 'Control detenido o con error de actuador'
        if not getattr(config, 'SERVO_MANUAL_ENABLED', False):
            return False, 'Control manual no habilitado'
        if self.state == self.PUMPING or self.pump.active:
            return False, 'Espera a que termine la bomba antes de mover la compuerta'
        if self.state not in (self.IDLE, self.FEED_OPEN, self.FEED_CLOSE):
            return False, 'Equipo ocupado'
        if opened and (self.food_target is not None or self.state != self.IDLE):
            return False, 'Cancela primero el servido automatico'
        if opened:
            if self.manual_food_started is not None:
                return False, 'Compuerta abierta; cierre automatico a 300 g activo'
            try:
                weight = self._food_weight(now_ms)
            except Exception as exc:
                return False, str(exc)
            if weight >= config.FOOD_TARGET_G:
                return False, 'El tazon ya alcanza 300 g; no se abre'
        pulse = config.SERVO_OPEN_US if opened else config.SERVO_CLOSED_US
        try:
            self.servo.move_us(pulse)
        except Exception as exc:
            self._actuator_fault('Error de compuerta manual: ' + repr(exc))
            return False, self.last_event
        self.food_target = None
        self.food_weigh_at = None
        self.manual_food_started = now_ms if opened else None
        self.state = self.IDLE
        self.servo_holding = True
        self.gate_command = 'abrir' if opened else 'cerrar'
        self.last_event = 'Orden de %s enviada: %s us; mantiene posicion' % (self.gate_command, pulse)
        self.food_result = ('Apertura manual; cierre automatico al llegar a 300 g'
                            if opened else 'Compuerta cerrada manualmente')
        self.request_beep(now_ms, duration_ms=200)
        return True, self.last_event

    def request_feed(self, now_ms, _batch=False):
        if self.manual_food_started is not None:
            return False, 'Primero cerrar la compuerta manual'
        if self.food_target is not None and not _batch:
            return False, 'Ya hay un servido de 300 g en curso'
        if not self.actions_allowed:
            return False, 'Modo diagnostico: servido bloqueado'
        if not getattr(config, 'SERVO_MOVEMENT_ENABLED', True):
            self.last_event = 'Compuerta bloqueada: revisar recorrido fisico antes de habilitar'
            return False, self.last_event
        if self.state != self.IDLE:
            return False, "Espera a que termine la accion actual"
        weight = self.status.get('weight_g')
        if (not self.status.get("calibrated") or not self.status.get('hx_ok')
                or isinstance(weight, bool) or not isinstance(weight, (int, float))
                or not math.isfinite(weight) or self._last_sensor_ms is None
                or self._diff(now_ms, self._last_sensor_ms) > config.WEIGHT_MAX_AGE_MS
                or (self.status.get('weight_age_ms') or 0) > config.WEIGHT_MAX_AGE_MS):
            return False, "Revisa HX711 y los archivos de calibracion antes de dispensar"
        if self.status["weight_g"] >= config.BOWL_MAX_WEIGHT_G:
            self.last_event = "Dispensado bloqueado: el plato ya tiene suficiente peso"
            return False, self.last_event
        try:
            self.servo.move_us(config.SERVO_OPEN_US)
            self.servo_holding = True
        except Exception as exc:
            self._actuator_fault("Error al activar servo: " + repr(exc))
            return False, self.last_event
        self.state = self.FEED_OPEN
        self.deadline = self._add(now_ms, config.SERVO_OPEN_TIME_MS)
        self.last_event = "Compuerta de alimento abierta por tiempo limitado"
        return True, self.last_event

    def _food_weight(self, now_ms):
        value = self.status.get('weight_control_g', self.status.get('weight_g'))
        age = self.status.get('weight_age_ms', 0)
        if (not self.status.get('calibrated') or not self.status.get('hx_ok')
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < -5
                or self._last_sensor_ms is None
                or self._diff(now_ms, self._last_sensor_ms) > config.WEIGHT_MAX_AGE_MS
                or age is None or age > config.WEIGHT_MAX_AGE_MS):
            raise ValueError('Pesa sin lectura valida y reciente; revisar montaje y tara')
        return value

    def request_food(self, now_ms):
        if not self.actions_allowed or self.fault or self.state != self.IDLE or self.food_target is not None or self.manual_food_started is not None:
            return False, 'Equipo ocupado o bloqueado'
        if not config.SERVO_MOVEMENT_ENABLED:
            return False, 'Servo bloqueado hasta validar fisicamente el montaje'
        try:
            weight = self._food_weight(now_ms)
        except Exception as exc:
            self.food_result = str(exc)
            return False, self.food_result
        if weight >= config.FOOD_TARGET_G:
            self.food_result = 'El tazon ya alcanza 300 g; no se sirve mas'
            return False, self.food_result
        self.food_target = config.FOOD_TARGET_G
        self.food_cycles = self.food_no_progress = 0
        self.food_started = now_ms
        self.food_last_weight = weight
        self.food_weigh_at = now_ms
        self.food_result = 'Servido solicitado: total objetivo 300 g en el tazon'
        return True, self.food_result

    def stop_food(self, now_ms):
        if self.manual_food_started is not None:
            return self.request_gate(False, now_ms)
        self.food_target = None
        self.food_result = 'Servido de alimento cancelado'
        if self.state == self.FEED_OPEN:
            try:
                self.servo.move_us(config.SERVO_CLOSED_US)
                self.state = self.FEED_CLOSE
                self.deadline = self._add(now_ms, config.SERVO_SETTLE_MS)
            except Exception as exc:
                self._actuator_fault('Error al cerrar durante parada: ' + repr(exc))
                return False, self.last_event
        return True, self.food_result

    def _manual_food_tick(self, now_ms):
        if self.manual_food_started is None:
            return
        reason = None
        try:
            weight = self._food_weight(now_ms)
            if weight >= config.FOOD_TARGET_G:
                reason = 'Cierre automatico: objetivo alcanzado %.1f g' % weight
            elif self._diff(now_ms, self.manual_food_started) >= config.FOOD_MAX_RUN_MS:
                reason = 'Cierre por tiempo maximo; revisar deposito y pesa'
        except Exception as exc:
            reason = 'Cierre por lectura de peso no valida: ' + str(exc)
        if reason:
            ok, _ = self.request_gate(False, now_ms)
            if ok:
                self.food_result = self.last_event = reason

    def _food_tick(self, now_ms):
        if self.food_target is None or self.state != self.IDLE:
            return
        if self._diff(now_ms, self.food_weigh_at) < 0:
            return
        try:
            weight = self._food_weight(now_ms)
            if weight >= self.food_target:
                self.food_result = 'Objetivo alcanzado: %.1f g; servido detenido' % weight
                self.food_target = None
                return
            if (self.food_cycles >= config.FOOD_MAX_CYCLES
                    or self._diff(now_ms, self.food_started) >= config.FOOD_MAX_RUN_MS):
                raise ValueError('Limite de tandas o tiempo; revisar salida de croquetas')
            if self.food_cycles:
                if weight < self.food_last_weight - 5:
                    raise ValueError('Peso disminuyo; no continuar mientras comen o mueven el tazon')
                self.food_no_progress = self.food_no_progress + 1 if weight - self.food_last_weight < 1 else 0
                if self.food_no_progress >= config.FOOD_NO_PROGRESS_CYCLES:
                    raise ValueError('No aumenta el peso; revisar deposito o atasco')
            ok, message = self.request_feed(now_ms, _batch=True)
            if not ok:
                raise ValueError(message)
            pulse = config.FOOD_FINE_PULSE_MS if self.food_target - weight < 30 else config.FOOD_PULSE_MS
            self.deadline = self._add(now_ms, pulse)
            self.food_cycles += 1
            self.food_last_weight = weight
            self.food_result = 'Tanda %s; peso previo %.1f g / 300 g' % (self.food_cycles, weight)
        except Exception as exc:
            self.food_target = None
            self.food_result = 'Servido detenido: ' + str(exc)

    def request_pump(self, now_ms, source='manual', command_id=None, test=False):
        if not self.actions_allowed:
            return False, 'Modo diagnostico: servido bloqueado'
        if self.state != self.IDLE:
            return False, "Espera a que termine la accion actual"
        if self.food_target is not None or self.manual_food_started is not None:
            return False, 'Primero terminar o cancelar el servido de alimento'
        if self._pump_ready_at is not None and self._diff(now_ms, self._pump_ready_at) < 0:
            return False, 'Espera 10 segundos entre servidos de agua'
        if len(self.water_events) > 30:
            return False, 'Registro MQTT pendiente; reconecta la PC antes de servir mas agua'
        if config.WATER_LEVEL_SENSOR_ENABLED and not self.status.get("water_available"):
            self.last_event = "Bomba bloqueada: flotador indica poca o nada de agua"
            return False, self.last_event
        try:
            if test:
                self.pump.on(duration_ms=3000)
            else:
                self.pump.on()
        except Exception as exc:
            self._actuator_fault("Error al activar bomba: " + repr(exc))
            return False, self.last_event
        duration = min(5000, config.PUMP_PULSE_MS, config.PUMP_MAX_ON_MS)
        if test:
            duration = min(duration, 3000)
        self._water_seq += 1
        self._water_run = {'run_id': self._boot_id + '-' + str(self._water_seq),
                           'started_ms': now_ms, 'requested_ms': duration,
                           'source': source, 'command_id': command_id}
        self.state = self.PUMPING
        self.deadline = self._add(now_ms, duration)
        self._water_event('started', now_ms, 'orden_manual')
        self.last_event = "Servido manual de agua; nivel no medido, supervisa el plato"
        return True, self.last_event

    def stop_pump(self, now_ms=None):
        if now_ms is None:
            now_ms = time.ticks_ms() if hasattr(time, 'ticks_ms') else int(time.monotonic()*1000)
        self.pump.off()
        if self.state == self.PUMPING:
            self._finish_water(now_ms, 'detenida_manualmente')

    def tick(self, now_ms):
        # Atender el plazo ANTES de leer sensores. Durante el pulso se conserva
        # la ultima lectura para no retrasar el apagado con HX711 o DHT.
        if self.state == self.PUMPING:
            if self._diff(now_ms, self.deadline) >= 0 or not self.pump.active:
                try:
                    self._finish_water(now_ms, 'tiempo_cumplido' if self._diff(now_ms, self.deadline) >= 0 else 'salida_desactivada')
                except Exception as exc:
                    self._actuator_fault('No se pudo apagar bomba: ' + repr(exc))
        if self.state == self.FEED_OPEN and self._diff(now_ms, self.deadline) >= 0:
            try:
                self.servo.move_us(config.SERVO_CLOSED_US)
                self.state = self.FEED_CLOSE
                self.deadline = self._add(now_ms, config.SERVO_SETTLE_MS)
                self.last_event = "Orden de cierre enviada; estabilizando servo"
            except Exception as exc:
                self._actuator_fault("No se pudo ordenar cierre: " + repr(exc))

        elif self.state == self.FEED_CLOSE and self._diff(now_ms, self.deadline) >= 0:
            self.state = self.IDLE
            if self.food_target is not None:
                self.food_weigh_at = self._add(now_ms, config.FOOD_WEIGH_WAIT_MS)
            self.last_event = "Racion terminada; PWM mantiene la compuerta cerrada"
            self._optional('buzzer', self.buzzer.on)
            self._last_beep_until = self._add(now_ms, 100)

        elif self.state == self.PUMPING:
            if config.WATER_LEVEL_SENSOR_ENABLED and not self.status.get("water_available"):
                self._finish_water(now_ms, 'nivel_bajo')
            elif self._diff(now_ms, self.deadline) >= 0:
                self._finish_water(now_ms, 'tiempo_cumplido')

        # No bloquear los plazos de la compuerta con DHT/HX711.
        reading_allowed = self.state in (self.IDLE, self.FAULT)
        if reading_allowed or (self.state == self.PUMPING and config.WATER_LEVEL_SENSOR_ENABLED):
            try:
                self.status = self.sensors.read(now_ms)
                self._last_sensor_ms = now_ms
            except Exception as exc:
                self.status = {'sensor_error': repr(exc), 'hx_ok': False,
                               'water_available': False, 'calibrated': False,
                               'weight_g': None, 'dht_ok': False}
                self.last_event = 'Error de lectura de sensores: ' + repr(exc)
                if self.state == self.PUMPING:
                    self._finish_water(now_ms, 'error_sensor')
        self.status['readings_paused'] = not reading_allowed
        self._manual_food_tick(now_ms)
        self._food_tick(now_ms)

        if self._last_beep_until is not None and self._diff(now_ms, self._last_beep_until) >= 0:
            self._optional('buzzer', self.buzzer.off)
            self._last_beep_until = None
        if self._signal_until is not None and self._diff(now_ms, self._signal_until) >= 0:
            self._signal_until = None
        return self.status

    def snapshot(self):
        data = dict(self.status)
        data["state"] = self.state
        data["last_event"] = self.last_event
        data['actuator_fault'] = self.fault
        data['aux_errors'] = dict(self.aux_errors)
        data['servo_enabled'] = config.SERVO_MOVEMENT_ENABLED
        data['servo_manual_enabled'] = getattr(config, 'SERVO_MANUAL_ENABLED', False)
        data['gate_command'] = self.gate_command
        data['buzzer_enabled'] = config.BUZZER_ENABLED
        data['servo_open_us'] = config.SERVO_OPEN_US
        data['servo_closed_us'] = config.SERVO_CLOSED_US
        data['servo_holding_pwm'] = self.servo_holding
        data['food_target_g'] = config.FOOD_TARGET_G
        data['food_active'] = self.food_target is not None or self.manual_food_started is not None
        data['manual_food_active'] = self.manual_food_started is not None
        data['food_cycles'] = self.food_cycles
        data['food_result'] = self.food_result
        data['water_duration_ms'] = config.PUMP_PULSE_MS
        data['actions_allowed'] = self.actions_allowed
        data['ia_signal_active'] = self._signal_until is not None
        data['water_mode'] = 'manual_supervisado'
        data['water_level_monitored'] = config.WATER_LEVEL_SENSOR_ENABLED
        if not config.WATER_LEVEL_SENSOR_ENABLED:
            data['water_available'] = None
        data['water_events_pending'] = len(self.water_events)
        data['session_id'] = self._boot_id
        return data

    def safe_shutdown(self):
        self.food_target = None
        self.manual_food_started = None
        self._signal_until = None
        # Una parada no debe ordenar otro movimiento de una compuerta trabada.
        self._optional('bomba', self.stop_pump)
        self._optional('buzzer', self.buzzer.off)
        self._optional('servo', self.servo.release)
        self.actions_allowed = False
        self.state = self.FAULT if self.fault else self.IDLE
