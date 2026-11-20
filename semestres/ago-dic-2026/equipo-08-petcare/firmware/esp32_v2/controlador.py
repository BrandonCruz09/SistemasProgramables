"""Control por plazos: sin sleep durante servido, cierre a 300 g y agua 5 s."""
import time
import math
import os
import binascii
import config

class PetCareController:
    IDLE = 'LISTO'
    FEED_OPEN = 'COMPUERTA_ABIERTA'
    FEED_CLOSE = 'COMPUERTA_CERRANDO'
    PUMPING = 'BOMBA_ACTIVA'

    def __init__(self, sensors, servo, pump, buzzer):
        self.sensors, self.servo, self.pump, self.buzzer = sensors, servo, pump, buzzer
        self.state = self.IDLE
        self.status = {}
        self.actions_allowed = True
        self.session = binascii.hexlify(os.urandom(8)).decode()
        self.errors = {}
        self.gate_command = None
        self.gate_test_open = False
        self.food_mode = None
        self.food_started = self.food_deadline = None
        self.last_weight = None
        self.cycles = self.no_progress = 0
        self.water_run = None
        self.water_events = []
        self.water_sequence = 0
        self.cooldown = None
        self.last_event = 'Inicio: salidas apagadas; calibracion leida sin modificar'
        self.food_result = 'Sin servido'

    def action_in_progress(self):
        return self.state != self.IDLE or self.food_mode is not None

    def weight(self, now):
        s = self.status
        g = s.get('weight_control_g')
        age = s.get('weight_age_ms')
        if (not s.get('hx_ok') or not s.get('calibrated') or type(g) not in (int, float)
                or not math.isfinite(g) or age is None or age > config.WEIGHT_MAX_AGE_MS or g < -5):
            raise ValueError('Pesa sin lectura valida; revisar RAW y calibracion conservada')
        return g

    def _move(self, opened):
        pulse = config.SERVO_OPEN_US if opened else config.SERVO_CLOSED_US
        self.servo.move_us(pulse)
        self.gate_command = 'abrir' if opened else 'cerrar'
        self.errors.pop('servo', None)

    def _close(self, reason):
        self._move(False)
        self.gate_test_open = False
        self.food_mode = None
        self.state = self.IDLE
        self.food_result = self.last_event = reason

    def request_gate(self, opened, now):
        if not self.actions_allowed:
            return False, 'Modo de comprobacion sin motores'
        if self.pump.active:
            return False, 'Termina primero el agua'
        try:
            if not opened:
                self._close('Cierre enviado: 1690 us; PWM conservado')
                return True, self.last_event
            if self.food_mode:
                return False, 'Compuerta ya en servido'
            if self.weight(now) >= config.FOOD_TARGET_G:
                return False, 'La lectura alcanza 300 g; no se abre'
            self._move(True)
            self.food_mode = 'manual'
            self.food_started = now
            self.state = self.FEED_OPEN
            self.last_event = 'Apertura enviada: 1350 us; cierre a 300 g activo'
            return True, self.last_event
        except Exception as exc:
            return False, str(exc)

    def request_gate_test(self, now):
        if not self.actions_allowed or self.action_in_progress():
            return False, 'Termina primero la accion en curso'
        try:
            self._move(True)
            self.gate_test_open = True
            self.last_event = 'Prueba sin croquetas: apertura 1350 us mantenida; cerrar manualmente'
            return True, self.last_event
        except Exception as exc:
            self.errors['servo'] = repr(exc)
            return False, 'Servo: ' + str(exc)

    def request_food(self, now):
        if not self.actions_allowed or self.action_in_progress() or self.gate_test_open:
            return False, 'Cierra la compuerta de prueba antes del servido automatico'
        try:
            g = self.weight(now)
            if g >= config.FOOD_TARGET_G:
                return False, 'El tazon ya alcanza 300 g'
            self.food_mode = 'auto'
            self.food_started = now
            self.food_deadline = now
            self.last_weight = g
            self.cycles = self.no_progress = 0
            self.last_event = 'Servido solicitado hasta 300 g totales'
            return True, self.last_event
        except Exception as exc:
            return False, str(exc)

    def stop_food(self, now):
        try:
            self._close('Alimento detenido; orden de cierre enviada')
            return True, self.last_event
        except Exception as exc:
            self.errors['servo'] = repr(exc)
            self.food_mode = None
            return False, 'Fallo al ordenar cierre: ' + str(exc)

    def request_beep(self, now, mode=None):
        if not self.actions_allowed:
            return False, 'Modo de comprobacion sin motores'
        try:
            self.buzzer.on(2000, mode)
            self.servo.verify()
            self.errors.pop('buzzer', None)
            return True, 'Senal de buzzer enviada; sonido fisico sin verificar'
        except Exception as exc:
            self.buzzer.off()
            self.errors['buzzer'] = repr(exc)
            return False, 'Buzzer: ' + str(exc)

    def _water_event(self, phase, now, reason):
        if self.water_run is None:
            return
        event = dict(self.water_run)
        event.update(id=event['run_id'] + '-' + phase, phase=phase,
                     uptime_ms=now, duration_ms=max(0,time.ticks_diff(now,event['started_ms'])),
                     reason=reason, volume_ml=None, physical_flow_verified=False,
                     water_level_monitored=False)
        self.water_events.append(event)

    def request_pump(self, now, source='manual', command_id=None):
        if not self.actions_allowed or self.action_in_progress():
            return False, 'Equipo ocupado o en diagnostico'
        if self.cooldown is not None and time.ticks_diff(now,self.cooldown)<0:
            return False, 'Espera 10 segundos entre servidos'
        if len(self.water_events)>28:
            return False, 'Esperando enviar el registro de agua a la PC'
        try:
            self.pump.on(5000)
            self.water_sequence += 1
            self.water_run = {'run_id':self.session+'-'+str(self.water_sequence),
                'started_ms':now,'requested_ms':5000,'source':source,'command_id':command_id}
            self._water_event('started',now,'orden_manual')
            self.state = self.PUMPING
            self.last_event = 'Rele activado por 5 s; flujo fisico sin verificar'
            return True,self.last_event
        except Exception as exc:
            self.errors['bomba']=repr(exc)
            return False,'Bomba: '+str(exc)

    def stop_pump(self, now=None, reason='detenida_manualmente'):
        now = time.ticks_ms() if now is None else now
        self.pump.off()
        if self.water_run:
            self._water_event('finished',now,reason)
            self.water_run=None
            self.cooldown=time.ticks_add(now,10000)
        if self.state==self.PUMPING:
            self.state=self.IDLE
        self.last_event='Agua: '+reason
        return True,self.last_event

    def request_signal(self, now):
        self.last_event='IA: deteccion registrada, sin servido automatico'
        return True,self.last_event

    def command(self, action, now, command_id=None, mode=None):
        if action=='gate_test_open':return self.request_gate_test(now)
        if action=='tone':return self.request_beep(now,'passive')
        if action=='gate_open':return self.request_gate(True,now)
        if action=='gate_close':return self.request_gate(False,now)
        if action=='feed':return self.request_food(now)
        if action=='stop_food':return self.stop_food(now)
        if action=='water':return self.request_pump(now,'mqtt_manual',command_id)
        if action=='stop_water':return self.stop_pump(now)
        if action=='beep':return self.request_beep(now,mode)
        if action=='signal_dog':return self.request_signal(now)
        return False,'Accion desconocida'

    def tick(self, now):
        # Apagados primero; el peso se atiende incluso con compuerta abierta.
        for name, action in (('bomba',lambda:self.pump.tick(now)),
                             ('buzzer',lambda:self.buzzer.tick(now))):
            try:action()
            except Exception as exc:self.errors[name]=repr(exc)
        if self.state==self.PUMPING and not self.pump.active:
            self.stop_pump(now,'tiempo_cumplido')
        try:
            self.status=self.sensors.read(now,slow=not self.action_in_progress())
        except Exception as exc:
            self.status={'hx_ok':False,'calibrated':False,'weight_g':None,'sensor_error':repr(exc)}
        if self.food_mode:
            try:
                g=self.weight(now)
                if g>=config.FOOD_TARGET_G:
                    self._close('Cierre a %.1f g; objetivo alcanzado'%g)
                elif time.ticks_diff(now,self.food_started)>=config.FOOD_MAX_RUN_MS:
                    self._close('Cierre por limite de tiempo de alimento')
                elif self.food_mode=='auto' and time.ticks_diff(now,self.food_deadline)>=0:
                    if self.state==self.FEED_OPEN:
                        self._move(False)
                        self.state=self.FEED_CLOSE
                        self.food_deadline=time.ticks_add(now,1200)
                    else:
                        if self.cycles:
                            self.no_progress=self.no_progress+1 if g-self.last_weight<1 else 0
                        if self.no_progress>=3 or self.cycles>=30:
                            self._close('No aumenta el peso; revisar atasco o deposito')
                        else:
                            self.last_weight=g
                            self._move(True)
                            self.state=self.FEED_OPEN
                            self.food_deadline=time.ticks_add(now,100 if 300-g<30 else 250)
                            self.cycles+=1
            except Exception as exc:
                try:self._close('Alimento detenido: '+str(exc))
                except Exception as closing:
                    self.errors['servo']=repr(closing)
                    self.food_mode=None
                    self.state=self.IDLE
        return self.snapshot()

    def snapshot(self):
        s=dict(self.status)
        s.update(state=self.state,last_event=self.last_event,session_id=self.session,
            actions_allowed=self.actions_allowed,servo_enabled=True,servo_manual_enabled=True,
            buzzer_enabled=config.BUZZER_ENABLED,servo_holding=self.servo.pwm is not None,
            servo_open_us=config.SERVO_OPEN_US,servo_closed_us=config.SERVO_CLOSED_US,
            servo_pulse_us=self.servo.pulse,gate_command=self.gate_command,
            gate_test_supported=True,gate_test_open=self.gate_test_open,
            manual_food_active=self.food_mode=='manual',food_active=self.food_mode is not None,food_target_g=300,food_result=self.food_result,
            pump_active=self.pump.active,water_duration_ms=5000,water_mode='manual_supervisado',
            water_level_monitored=False,water_available=None,aux_errors=dict(self.errors),
            firmware_version=config.VERSION,calibration_automatic=False)
        return s

    def safe_shutdown(self):
        self.actions_allowed=False
        self.food_mode=None
        for action in (self.pump.off,self.buzzer.off,self.servo.release):
            try:action()
            except Exception as exc:print('Parada:',repr(exc))
