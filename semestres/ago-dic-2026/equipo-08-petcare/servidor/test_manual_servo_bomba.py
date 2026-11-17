import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import test_petcare
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'firmware/pruebas'))
import PRUEBA_MANUAL_SERVO_BOMBA as prueba


class ManualTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(prueba.time,'ticks_diff',lambda a,b:a-b,create=True)
        p.start(); self.addCleanup(p.stop)
        self.pump=Mock(); self.pump.active=False
        self.pump.on.side_effect=lambda **kw:setattr(self.pump,'active',True)
        self.pump.off.side_effect=lambda:setattr(self.pump,'active',False)
        self.servo=Mock()
        self.c=prueba.ControlManual(self.pump,self.servo)

    def test_sin_orden_no_mueve_y_salir_apaga(self):
        self.c.tick(10000)
        self.pump.on.assert_not_called(); self.servo.move_us.assert_not_called()
        self.c.comando('0',10000)
        self.pump.off.assert_called(); self.servo.release.assert_called()

    def test_apertura_y_cierre_correctos(self):
        self.c.comando('1',0); self.c.comando('2',100)
        self.assertEqual([c.args[0] for c in self.servo.move_us.call_args_list],[1350,1690])

    def test_apaga_sin_entrada_ni_callback_del_timer(self):
        self.c.comando('3',100)
        self.c.tick(3099); self.assertTrue(self.pump.active)
        self.c.tick(3100); self.assertFalse(self.pump.active)
        self.assertIsNone(self.c.inicio_bomba)

    def test_bloqueo_en_ambas_direcciones(self):
        self.c.comando('1',0)
        self.assertFalse(self.c.comando('3',100)[0])
        self.pump.on.assert_not_called()
        self.c.comando('5',200)
        self.assertTrue(self.c.comando('3',300)[0])
        self.assertFalse(self.c.comando('2',400)[0])
        self.assertEqual(self.servo.move_us.call_count,1)

    def test_repetir_no_extiende_tiempo_y_parada_manual(self):
        self.c.comando('3',0)
        self.assertFalse(self.c.comando('3',2000)[0])
        self.assertEqual(self.c.inicio_bomba,0)
        self.c.comando('4',2100)
        self.assertFalse(self.pump.active)
        self.c.tick(3000)
        self.pump.on.assert_called_once_with(duration_ms=3000)

    def test_error_pwm_apaga_y_bloquea(self):
        self.servo.move_us.side_effect=RuntimeError('PWM')
        self.assertFalse(self.c.comando('1',0)[0])
        self.assertTrue(self.c.terminado)
        self.c.comando('3',100)
        self.pump.on.assert_not_called()
        self.pump.off.assert_called(); self.servo.release.assert_called()

    def test_parada_intenta_ambos_aunque_uno_falle(self):
        self.pump.off.side_effect=OSError('pin')
        with self.assertRaises(RuntimeError):self.c.detener()
        self.servo.release.assert_called_once()
        self.assertTrue(self.c.terminado)

    def test_invalidos_no_activan_nada(self):
        for option in ('','abc','33','-1'):
            self.assertFalse(self.c.comando(option,0)[0])
        self.pump.on.assert_not_called(); self.servo.move_us.assert_not_called()


if __name__=='__main__': unittest.main()
