import json,sys,unittest,time
from unittest.mock import Mock,patch
import test_petcare
import config
from mqtt_link import MQTTLink
from dashboard import DashboardState

class GateTests(unittest.TestCase):
    def setUp(self):
        self.c=test_petcare.PetCareTests().make_controller(calibrated=False,weight=None)
        self.c.tick(0)

    def test_manual_sin_pesa_ni_auto_y_mantiene_pwm(self):
        with patch.object(config,'SERVO_MOVEMENT_ENABLED',False):
            self.assertTrue(self.c.request_gate(True,0)[0])
            self.c.tick(60000)
            self.assertEqual(self.c.servo.angles,[1350])
            self.assertEqual(self.c.servo.released,0)
            self.assertTrue(self.c.request_gate(False,60001)[0])
            self.c.tick(120000)
            self.assertEqual(self.c.servo.angles,[1350,1690])
            self.assertEqual(self.c.servo.released,0)
            self.assertFalse(self.c.request_food(120000)[0])

    def test_no_mueve_al_iniciar(self):
        self.c.tick(10000)
        self.assertEqual(self.c.servo.angles,[])
        self.assertIsNone(self.c.snapshot()['gate_command'])

    def test_no_simultaneo_con_bomba_ni_en_diagnostico(self):
        self.assertTrue(self.c.request_pump(0)[0])
        self.assertFalse(self.c.request_gate(True,1)[0])
        self.assertFalse(self.c.request_gate(False,1)[0])
        self.c.stop_pump(2)
        self.c.actions_allowed=False
        self.assertFalse(self.c.request_gate(True,3)[0])
        self.assertEqual(self.c.servo.angles,[])

    def test_error_de_pwm_no_marca_orden_aplicada(self):
        self.c.servo.move_us=Mock(side_effect=OSError('PWM'))
        self.assertFalse(self.c.request_gate(True,0)[0])
        self.assertEqual(self.c.state,self.c.FAULT)
        self.assertFalse(self.c.pump.active)
        self.assertIsNone(self.c.gate_command)

    def test_mqtt_sesion_actual_y_no_repetir(self):
        m=MQTTLink();m.client=Mock()
        cmd={'action':'gate_open','id':'manual-1','session_id':'vieja'}
        m.pending_command=cmd;m._run_command(self.c,0)
        self.assertEqual(self.c.servo.angles,[])
        cmd={'action':'gate_open','id':'manual-2','session_id':self.c.snapshot()['session_id']}
        m._on_message(m.command_topic,json.dumps(cmd).encode());m._run_command(self.c,1)
        m._on_message(m.command_topic,json.dumps(cmd).encode());m._run_command(self.c,2)
        self.assertEqual(self.c.servo.angles,[1350])
        cmd.update(action='gate_close',id='manual-3')
        m._on_message(m.command_topic,json.dumps(cmd).encode());m._run_command(self.c,3)
        self.assertEqual(self.c.servo.angles,[1350,1690])

    def test_dashboard_capacidad_y_datos_recientes(self):
        d=DashboardState();d.update({'status':self.c.snapshot()})
        self.assertTrue(d.request_command('gate_open')[0])
        self.assertEqual(d.commands.get()['action'],'gate_open')
        self.assertTrue(d.request_command('gate_close')[0])
        d.commands.get();d.received-=20
        self.assertFalse(d.request_command('gate_open')[0])
        d.update({'status':dict(self.c.snapshot(),servo_manual_enabled=False)})
        self.assertFalse(d.request_command('gate_close')[0])

    def test_buzzer_solo_no_mueve_salidas_y_se_apaga(self):
        self.assertTrue(self.c.request_beep(0)[0])
        self.assertTrue(self.c.buzzer.active)
        self.assertEqual(self.c.servo.angles,[])
        self.assertFalse(self.c.pump.active)
        self.c.tick(1999)
        self.assertTrue(self.c.buzzer.active)
        self.c.tick(2000)
        self.assertFalse(self.c.buzzer.active)

    def test_manual_emite_sonido_sin_usar_pwm_del_buzzer(self):
        self.c.request_gate(True,0)
        self.assertTrue(self.c.buzzer.active)
        self.c.tick(200)
        self.assertFalse(self.c.buzzer.active)
        self.assertEqual(self.c.servo.angles,[1350])

    def test_pir_publica_cambio_antes_de_diez_segundos(self):
        m=MQTTLink();m.client=Mock()
        with patch.object(config,'MQTT_HOST','localhost'), patch.object(m,'_elapsed',side_effect=lambda a,b:999999 if b is None else a-b):
            m.poll(0,self.c)
            initial=m.client.publish.call_count
            self.c.status['pir']=True
            m.poll(500,self.c)
            self.assertEqual(m.client.publish.call_count,initial+1)
            payload=json.loads(m.client.publish.call_args.args[1])
            self.assertTrue(payload['status']['pir'])
            self.c.status['pir']=False
            m.poll(1000,self.c)
            self.assertEqual(m.client.publish.call_count,initial+2)

if __name__=='__main__':unittest.main()

