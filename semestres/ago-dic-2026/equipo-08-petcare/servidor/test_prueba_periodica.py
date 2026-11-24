# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Comprobar mediante pruebas de software el módulo prueba periodica de PetCare.

import unittest
from unittest.mock import patch
import test_petcare
import config
from prueba_periodica import PruebaPeriodica
from mqtt_link import MQTTLink


class Pump(test_petcare.FakePump):
    def __init__(self):
        super().__init__()
        self.calls = []
    def on(self, duration_ms=None):
        self.active = True
        self.calls.append(duration_ms)


class PeriodicaTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(config, 'SERVO_MOVEMENT_ENABLED', True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def make(self, weight=0):
        c = test_petcare.PetCareTests().make_controller(weight=weight)
        c.pump = Pump()
        c.tick(0)
        c.status['hx_ok'] = True
        return c

    def test_tres_ciclos_con_pwm_mantenido_sin_repetir_al_terminar(self):
        c = self.make()
        p = PruebaPeriodica(c, 0)
        for t in (0, 29999):
            c.tick(t); p.tick(t)
        self.assertEqual(c.servo.angles, [])
        for start in (30000, 60000, 90000):
            for t in (start, start+900, start+1250, start+3000, start+6000):
                c.tick(t); p.tick(t)
        self.assertEqual(p.phase, 'terminada')
        self.assertEqual(c.pump.calls, [3000,3000,3000])
        self.assertEqual(c.servo.angles, [850,1500]*3)
        self.assertFalse(c.pump.active)
        c.tick(150000); p.tick(150000)
        self.assertEqual(len(c.pump.calls), 3)

    def test_tara_desplazada_impide_iniciar(self):
        with self.assertRaises(ValueError): PruebaPeriodica(self.make(67), 0)

    def test_respeta_bloqueo_servo(self):
        with patch.object(config, 'SERVO_MOVEMENT_ENABLED', False, create=True):
            with self.assertRaises(ValueError): PruebaPeriodica(self.make(), 0)

    def test_detener_agua_cancela_ciclos_siguientes(self):
        c = self.make(); p = PruebaPeriodica(c, 0)
        c.request_pump(33000, test=True)
        p.phase = 'agua'
        c.stop_pump(34000); c.tick(34000); p.tick(34000)
        self.assertEqual(p.phase, 'error')
        c.tick(60000); p.tick(60000)
        self.assertEqual(len(c.pump.calls), 1)

    def test_mqtt_en_prueba_solo_acepta_parada(self):
        m = MQTTLink(); m.accept_actions = False
        m._on_message(m.command_topic, b'{"action":"feed","id":"test"}')
        self.assertIsNone(m.pending_command)
        m._on_message(m.command_topic, b'{"action":"stop_water","id":"stop"}')
        self.assertEqual(m.pending_command['action'], 'stop_water')


if __name__ == '__main__': unittest.main()
