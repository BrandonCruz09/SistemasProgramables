# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Comprobar mediante pruebas de software el módulo servido objetivo de PetCare.

import unittest
from unittest.mock import Mock, patch
import test_petcare
import config


class TargetTests(unittest.TestCase):
    def setUp(self):
        p = patch.object(config, 'SERVO_MOVEMENT_ENABLED', True)
        p.start(); self.addCleanup(p.stop)
        self.c = test_petcare.PetCareTests().make_controller()
        self.c.tick(0)

    def cycle(self, start, weight):
        c = self.c
        c.tick(start)
        c.tick(start + 250)
        c.tick(start + 600)
        c.sensors.weight = weight
        c.tick(start + 1800)

    def test_tandas_hasta_300_sin_reabrir(self):
        c = self.c
        self.assertTrue(c.request_food(0)[0])
        self.cycle(0, 280)
        self.assertEqual(c.deadline, 1900)  # Ultima tanda mas corta.
        c.tick(1900); c.tick(2250)
        c.sensors.weight = 302
        c.tick(3450)
        self.assertIsNone(c.food_target)
        self.assertEqual(c.servo.angles, [850,1500,850,1500])
        c.tick(10000)
        self.assertEqual(len(c.servo.angles), 4)

    def test_no_anade_300_a_lo_que_ya_hay(self):
        c=self.c; c.sensors.weight=300; c.tick(800)
        self.assertFalse(c.request_food(800)[0]); self.assertEqual(c.servo.angles, [])

    def test_lectura_invalida_detiene_sin_reintento(self):
        c=self.c; c.request_food(0); self.cycle(0, float('nan'))
        self.assertIsNone(c.food_target)
        self.assertEqual(c.servo.angles, [850,1500])
        c.tick(5000); self.assertEqual(len(c.servo.angles),2)

    def test_no_caen_croquetas_limita_tandas(self):
        c=self.c; c.request_food(0)
        for start in (0,1800,3600): self.cycle(start,0)
        self.assertIsNone(c.food_target)
        self.assertEqual(c.food_cycles,3)
        self.assertIn('No aumenta', c.food_result)

    def test_peso_disminuye_cancela(self):
        c=self.c; c.sensors.weight=100; c.tick(800); c.request_food(800)
        self.cycle(800,90)
        self.assertIsNone(c.food_target)
        self.assertIn('disminuyo',c.food_result)

    def test_no_duplica_ni_activa_agua_durante_comida(self):
        c=self.c; self.assertTrue(c.request_food(0)[0])
        self.assertFalse(c.request_food(0)[0]); self.assertFalse(c.request_pump(0)[0])

    def test_cancelar_cierra_y_no_reabre(self):
        c=self.c; c.request_food(0); c.tick(0)
        self.assertTrue(c.stop_food(50)[0]); c.tick(400); c.tick(3000)
        self.assertIsNone(c.food_target); self.assertEqual(c.servo.angles,[850,1500])

    def test_agua_corta_a_cinco_segundos(self):
        c=self.c; c.request_pump(0)
        self.assertTrue(c.action_in_progress()); c.tick(4999)
        self.assertTrue(c.pump.active); c.tick(5000)
        self.assertFalse(c.pump.active); self.assertFalse(c.action_in_progress())

    def test_error_apagado_no_reintenta_servir(self):
        c=self.c; c.request_pump(0); c.pump.off=Mock(side_effect=OSError('GPIO'))
        c.tick(5000)
        self.assertEqual(c.state,c.FAULT); self.assertFalse(c.request_pump(6000)[0])

    def test_dht_no_bloquea_comida_si_pesa_sana(self):
        c=self.c; c.status.update(dht_ok=False,dht_error='116')
        self.assertTrue(c.request_food(0)[0])

    def test_pwm_mantenido_permite_bomba_sin_cambiar_servo(self):
        c=self.c; c.request_feed(0); c.tick(900); c.tick(1250)
        self.assertEqual(c.state,c.IDLE)
        angles = list(c.servo.angles)
        self.assertTrue(c.request_pump(1300)[0])
        c.tick(6300)
        self.assertFalse(c.pump.active)
        self.assertEqual(c.servo.angles, angles)
        self.assertEqual(c.servo.released, 0)

    def test_sin_movimiento_automatico_con_servo_bloqueado(self):
        with patch.object(config,'SERVO_MOVEMENT_ENABLED',False):
            self.assertFalse(self.c.request_food(0)[0])


if __name__=='__main__': unittest.main()
