"""Control por plazos: sin sleep durante servido, cierre a 300 g y agua 5 s."""

import time
import math
import os
import binascii
import config


class PetCareController:
    IDLE = "LISTO"
    FEED_OPEN = "COMPUERTA_ABIERTA"
    FEED_CLOSE = "COMPUERTA_CERRANDO"
    PUMPING = "BOMBA_ACTIVA"
    FAULT = "ERROR_SALIDAS"

    def __init__(self, sensors, servo, pump, buzzer):
        self.sensors, self.servo, self.pump, self.buzzer = sensors, servo, pump, buzzer
        self.state = self.IDLE
        self.status = {}
        self.actions_allowed = True
        # La deteccion de la camara no debe activar actuadores hasta que el
        # operador habilite expresamente el modo automatico desde el panel.
        self.auto_armed = False
        self.session = binascii.hexlify(os.urandom(8)).decode()
        self.errors = {}
        self.gate_command = None
        self.food_mode = None
        self.food_started = self.food_deadline = None
        self.last_weight = None
        self.cycles = self.no_progress = 0
        self.water_run = None
        self.water_events = []
        self.water_sequence = 0
        self.cooldown = None
        self.auto_food_after = self.auto_water_after = self.water_pending_until = None
        self.water_events_dropped = 0
        self.last_event = "Inicio: salidas apagadas; calibracion leida sin modificar"
        self.food_result = "Sin servido"

    def action_in_progress(self):
        return (
            self.pump.active
            or self.state in (self.FEED_OPEN, self.FEED_CLOSE, self.PUMPING)
            or self.food_mode is not None
        )

    def weight(self, now):
        s = self.status
        g = s.get("weight_control_g")
        age = s.get("weight_age_ms")
        if (
            not s.get("hx_ok")
            or not s.get("calibrated")
            or type(g) not in (int, float)
            or not math.isfinite(g)
            or age is None
            or age > config.WEIGHT_MAX_AGE_MS
            or g < -5
        ):
            raise ValueError("Pesa sin lectura valida; revisar RAW y calibracion conservada")
        return g

    def _cue(self, kind):
        try:
            self.buzzer.cue(kind)
            self.errors.pop("buzzer", None)
        except Exception as exc:
            # Una falla del buzzer no debe cancelar ni bloquear un actuador.
            self.errors["buzzer"] = repr(exc)

    def _move(self, opened, sound=False):
        pulse = config.SERVO_OPEN_US if opened else config.SERVO_CLOSED_US
        self.servo.move_us(pulse)
        self.gate_command = "abrir" if opened else "cerrar"
        self.errors.pop("servo", None)
        if sound:
            self._cue("gate")

    def _close(self, reason, sound=False):
        self._move(False, sound=sound)
        self.food_mode = None
        self.state = self.IDLE
        self.food_result = self.last_event = reason

    def request_gate(self, opened, now):
        if not self.actions_allowed:
            return False, "Modo de comprobacion sin motores"
        if self.pump.active:
            return False, "Termina primero el agua"
        try:
            if not opened:
                self._close("Cierre enviado; PWM conservado", sound=True)
                return True, self.last_event
            if self.state == self.FAULT or self.food_mode:
                return False, "Compuerta ocupada o con error de salida"
            if self.weight(now) >= config.FOOD_TARGET_G:
                return False, "La lectura alcanza 300 g; no se abre"
            self._move(True, sound=True)
            self.food_mode = "manual"
            self.food_started = now
            self.auto_food_after = time.ticks_add(now, config.AUTO_FOOD_COOLDOWN_MS)
            self.state = self.FEED_OPEN
            self.last_event = "Apertura enviada: %d us; cierre a 300 g activo" % config.SERVO_OPEN_US
            return True, self.last_event
        except Exception as exc:
            return False, str(exc)

    def request_gate_position(self, pulse, now):
        low = min(config.SERVO_OPEN_US, config.SERVO_CLOSED_US)
        high = max(config.SERVO_OPEN_US, config.SERVO_CLOSED_US)
        if type(pulse) is not int or not low <= pulse <= high:
            return False, "Posicion fuera del recorrido configurado"
        if pulse == config.SERVO_CLOSED_US:
            return self.request_gate(False, now)
        if not self.actions_allowed or self.pump.active or self.state == self.FAULT:
            return False, "No se puede mover la compuerta en este estado"
        adjusting = self.food_mode == "manual" and self.state == self.FEED_OPEN
        if self.food_mode and not adjusting:
            return False, "Termina primero el servido actual"
        try:
            g = self.weight(now)
            if g >= config.FOOD_TARGET_G:
                return False, "La lectura alcanza 300 g; no se abre"
            self.servo.move_us(pulse)
            self.gate_command = "posicion_manual"
            self.errors.pop("servo", None)
            if not adjusting:
                self.food_mode = "manual"
                self.food_started = now
                self.auto_food_after = time.ticks_add(now, config.AUTO_FOOD_COOLDOWN_MS)
            self.state = self.FEED_OPEN
            self._cue("gate")
            self.last_event = "Posicion manual enviada: %d us; cierre supervisado activo" % pulse
            return True, self.last_event
        except Exception as exc:
            return False, str(exc)

    def request_food(self, now):
        if (
            not self.actions_allowed
            or self.action_in_progress()
            or self.state == self.FAULT
        ):
            return False, "Cierra la compuerta de prueba antes del servido automatico"
        try:
            g = self.weight(now)
            if g >= config.FOOD_TARGET_G:
                return False, "El tazon ya alcanza 300 g"
            self.food_mode = "auto"
            self.food_started = now
            self.auto_food_after = time.ticks_add(now, config.AUTO_FOOD_COOLDOWN_MS)
            self.food_deadline = now
            self.last_weight = g
            self.cycles = self.no_progress = 0
            self.last_event = "Servido solicitado hasta 300 g totales"
            return True, self.last_event
        except Exception as exc:
            return False, str(exc)

    def stop_food(self, now):
        self.water_pending_until = None
        try:
            self._close("Alimento detenido; orden de cierre enviada", sound=True)
            return True, self.last_event
        except Exception as exc:
            self.errors["servo"] = repr(exc)
            self.food_mode = None
            self.state = self.FAULT
            self.gate_command = "cierre_fallido"
            return False, "Fallo al ordenar cierre: " + str(exc)

    def handle_fault(self, exc, now):
        """Detiene una operacion fallida sin volver a abrir automaticamente."""
        self.errors["control"] = repr(exc)
        self.water_pending_until = None
        was_feeding = self.food_mode is not None
        self.food_mode = None
        for name, action in (
            ("bomba", lambda: self.stop_pump(now, "error_control")),
            ("buzzer", self.buzzer.off),
        ):
            try:
                action()
            except Exception as stopping:
                self.errors[name] = repr(stopping)
        if was_feeding:
            self.stop_food(now)
        self.state = self.FAULT
        self.last_event = "Error de control; parada solicitada, revisar salidas"

    def request_beep(self, now, mode=None):
        if not self.actions_allowed:
            return False, "Modo de comprobacion sin motores"
        try:
            self.buzzer.on(2000, mode)
            self.servo.verify()
            self.errors.pop("buzzer", None)
            return True, "Senal de buzzer enviada; sonido fisico sin verificar"
        except Exception as exc:
            self.errors["buzzer"] = repr(exc)
            try:
                self.buzzer.off()
            except Exception as stopping:
                self.errors["buzzer_parada"] = repr(stopping)
            return False, "Buzzer: " + str(exc)

    def _water_event(self, phase, now, reason):
        if self.water_run is None:
            return
        event = dict(self.water_run)
        event.update(
            id=event["run_id"] + "-" + phase,
            phase=phase,
            uptime_ms=now,
            duration_ms=max(0, time.ticks_diff(now, event["started_ms"])),
            reason=reason,
            volume_ml=None,
            physical_flow_verified=False,
            water_level_monitored=False,
        )
        self.water_events.append(event)

    def request_pump(self, now, source="manual", command_id=None):
        if not self.actions_allowed or self.action_in_progress() or self.state == self.FAULT:
            return False, "Equipo ocupado o en diagnostico"
        if self.cooldown is not None and time.ticks_diff(now, self.cooldown) < 0:
            return False, "Espera 10 segundos entre servidos"
        if len(self.water_events) > 28:
            self.water_events_dropped += len(self.water_events) - 20
            self.water_events = self.water_events[-20:]
        try:
            self.pump.on(config.PUMP_PULSE_MS)
            self._cue("water")
            self.water_sequence += 1
            self.water_run = {
                "run_id": self.session + "-" + str(self.water_sequence),
                "started_ms": now,
                "requested_ms": config.PUMP_PULSE_MS,
                "source": source,
                "command_id": command_id,
            }
            self._water_event(
                "started", now, "orden_automatica" if source == "auto_ia" else "orden_manual"
            )
            self.auto_water_after = time.ticks_add(now, config.AUTO_WATER_COOLDOWN_MS)
            self.water_pending_until = None
            self.state = self.PUMPING
            self.last_event = "Agua activada por 5 s; flujo fisico sin verificar"
            return True, self.last_event
        except Exception as exc:
            self.errors["bomba"] = repr(exc)
            return False, "Bomba: " + str(exc)

    def stop_pump(self, now=None, reason="detenida_manualmente"):
        now = time.ticks_ms() if now is None else now
        self.water_pending_until = None
        self.pump.off()
        if self.water_run:
            self._water_event("finished", now, reason)
            self.water_run = None
            self.cooldown = time.ticks_add(now, 10000)
        if self.state == self.PUMPING:
            self.state = self.IDLE
        self.last_event = "Agua: " + reason
        return True, self.last_event

    def request_signal(self, now):
        if (
            not config.AUTO_SERVE_ENABLED
            or not self.auto_armed
            or not self.actions_allowed
            or self.state == self.FAULT
        ):
            self.last_event = "IA: deteccion registrada, sin servido automatico"
            return True, self.last_event
        self._expire_auto_deadlines(now)
        partes = []
        if self.auto_food_after is None and not self.action_in_progress():
            try:
                g = self.weight(now)
            except ValueError:
                g = None
            if g is None:
                partes.append("comida: pesa sin lectura valida")
            elif g < config.FOOD_EMPTY_G:
                partes.append("comida: " + self.request_food(now)[1])
        if self.auto_water_after is None and self.water_pending_until is None:
            self.water_pending_until = time.ticks_add(now, config.AUTO_WATER_PENDING_MS)
            partes.append("agua 5 s en cola")
        self.last_event = "IA: perro; " + ("; ".join(partes) or "pausa entre servidos")
        return True, self.last_event

    def _expire_auto_deadlines(self, now):
        for name in ("auto_food_after", "auto_water_after", "water_pending_until"):
            deadline = getattr(self, name)
            if deadline is not None and time.ticks_diff(now, deadline) >= 0:
                setattr(self, name, None)

    def _auto_tick(self, now):
        self._expire_auto_deadlines(now)
        if (
            not config.AUTO_SERVE_ENABLED
            or not self.auto_armed
            or not self.actions_allowed
            or self.state == self.FAULT
        ):
            self.water_pending_until = None
            return
        if (
            self.water_pending_until is not None
            and not self.action_in_progress()
        ):
            self.water_pending_until = None
            self.request_pump(now, "auto_ia")

    def command(self, action, now, command_id=None, mode=None, position_us=None):
        if action == "auto_enable":
            if not config.AUTO_SERVE_ENABLED:
                return False, "La automatizacion esta deshabilitada en la configuracion"
            self.auto_armed = True
            self.last_event = "Modo automatico habilitado manualmente; se desarmara al reiniciar"
            return True, self.last_event
        if action == "auto_disable":
            self.auto_armed = False
            self.water_pending_until = None
            if self.food_mode == "auto":
                self.stop_food(now)
            elif self.water_run and self.water_run.get("source") == "auto_ia":
                self.stop_pump(now, "automatizacion_deshabilitada")
            self.last_event = "Modo automatico deshabilitado; servidos manuales siguen disponibles"
            return True, self.last_event
        if action == "tone":
            return self.request_beep(now, "passive")
        if action == "gate_open":
            return self.request_gate(True, now)
        if action == "gate_close":
            return self.request_gate(False, now)
        if action == "gate_position":
            return self.request_gate_position(position_us, now)
        if action == "feed":
            return self.request_food(now)
        if action == "stop_food":
            return self.stop_food(now)
        if action == "water":
            return self.request_pump(now, "mqtt_manual", command_id)
        if action == "stop_water":
            return self.stop_pump(now)
        if action == "beep":
            return self.request_beep(now, mode)
        if action == "signal_dog":
            return self.request_signal(now)
        return False, "Accion desconocida"

    def tick(self, now):
        # Apagados primero; el peso se atiende incluso con compuerta abierta.
        for name, action in (
            ("bomba", lambda: self.pump.tick(now)),
            ("buzzer", lambda: self.buzzer.tick(now)),
        ):
            try:
                action()
            except Exception as exc:
                self.errors[name] = repr(exc)
                self.handle_fault(exc, now)
        if self.state == self.PUMPING and not self.pump.active:
            self.stop_pump(now, "tiempo_cumplido")
        try:
            self.status = self.sensors.read(now, slow=not self.action_in_progress())
        except Exception as exc:
            self.status = {
                "hx_ok": False,
                "calibrated": False,
                "weight_g": None,
                "sensor_error": repr(exc),
            }
        if self.food_mode:
            try:
                g = self.weight(now)
                if g >= config.FOOD_TARGET_G:
                    self._close("Cierre a %.1f g; objetivo alcanzado" % g, sound=True)
                elif time.ticks_diff(now, self.food_started) >= config.FOOD_MAX_RUN_MS:
                    self._close("Cierre por limite de tiempo de alimento", sound=True)
                elif self.food_mode == "auto" and time.ticks_diff(now, self.food_deadline) >= 0:
                    if self.state == self.FEED_OPEN:
                        self._move(False, sound=True)
                        self.state = self.FEED_CLOSE
                        self.food_deadline = time.ticks_add(now, config.FOOD_WEIGH_WAIT_MS)
                    else:
                        if self.cycles:
                            self.no_progress = (
                                self.no_progress + 1 if g - self.last_weight < 1 else 0
                            )
                        if self.no_progress >= 3 or self.cycles >= 30:
                            self._close("No aumenta el peso; revisar atasco o deposito", sound=True)
                        else:
                            self.last_weight = g
                            self._move(True, sound=True)
                            self.state = self.FEED_OPEN
                            self.food_deadline = time.ticks_add(
                                now,
                                (
                                    config.FOOD_FINE_PULSE_MS
                                    if config.FOOD_TARGET_G - g < 30
                                    else config.FOOD_PULSE_MS
                                ),
                            )
                            self.cycles += 1
            except Exception as exc:
                try:
                    self._close("Alimento detenido: " + str(exc))
                except Exception as closing:
                    self.errors["servo"] = repr(closing)
                    self.food_mode = None
                    self.state = self.FAULT
                    self.gate_command = "cierre_fallido"
                    self.last_event = "Fallo al ordenar cierre; revisar compuerta"
        try:
            self._auto_tick(now)
        except Exception as exc:
            self.handle_fault(exc, now)
        return self.snapshot()

    def snapshot(self):
        s = dict(self.status)
        s.update(
            state=self.state,
            last_event=self.last_event,
            session_id=self.session,
            actions_allowed=self.actions_allowed,
            servo_enabled=True,
            servo_manual_enabled=True,
            buzzer_enabled=config.BUZZER_ENABLED,
            servo_holding=self.servo.pwm is not None,
            servo_open_us=config.SERVO_OPEN_US,
            servo_closed_us=config.SERVO_CLOSED_US,
            servo_pulse_us=self.servo.pulse,
            gate_command=self.gate_command,
            manual_food_active=self.food_mode == "manual",
            food_active=self.food_mode is not None,
            food_target_g=config.FOOD_TARGET_G,
            food_result=self.food_result,
            pump_active=self.pump.active,
            water_duration_ms=config.PUMP_PULSE_MS,
            water_mode=(
                "manual_y_automatico_armado"
                if self.auto_armed
                else "manual_y_automatico_disarmado"
            )
            if config.AUTO_SERVE_ENABLED
            else "manual_supervisado",
            auto_serve_available=config.AUTO_SERVE_ENABLED,
            auto_serve_enabled=self.auto_armed,
            auto_food_ready=self.auto_food_after is None,
            auto_water_ready=self.auto_water_after is None,
            auto_water_pending=self.water_pending_until is not None,
            water_events_dropped=self.water_events_dropped,
            water_level_monitored=False,
            water_available=None,
            aux_errors=dict(self.errors),
            firmware_version=config.VERSION,
            calibration_automatic=False,
        )
        return s

    def safe_shutdown(self):
        self.actions_allowed = False
        self.water_pending_until = None
        self.food_mode = None
        for action in (self.pump.off, self.buzzer.off, self.servo.release):
            try:
                action()
            except Exception as exc:
                print("Parada:", repr(exc))
