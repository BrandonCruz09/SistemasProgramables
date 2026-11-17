import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class CompuertaPruebaTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'firmware/pruebas/PRUEBA_SERVO_COMPUERTA.py'
        spec = importlib.util.spec_from_file_location('prueba_compuerta_test', path)
        self.mod = importlib.util.module_from_spec(spec)
        self.pin = Mock()
        pin_cls = Mock(return_value=self.pin)
        self.hardware = types.SimpleNamespace(Pin=pin_cls, PWM=Mock())
        self.patch = patch.dict(sys.modules, {'machine': self.hardware})
        self.patch.start()
        spec.loader.exec_module(self.mod)
        self.servo = self.mod.PruebaCompuerta()

    def tearDown(self):
        self.patch.stop()

    def test_arranque_y_ciclo_sin_confirmar_no_mueven(self):
        self.servo.ciclo()
        self.hardware.PWM.assert_not_called()

    def test_ciclo_limitado_y_liberacion(self):
        self.servo.ajustes_confirmados = True
        self.servo.mover = Mock()
        self.servo.ciclo()
        self.assertEqual([c.args for c in self.servo.mover.call_args_list],
                         [(800, 900), (1850, 350), (1700, 250), (1850, 500)])
        self.pin.value.assert_called_with(0)

    def test_cancelacion_no_intenta_otro_cierre(self):
        self.servo.pwm = Mock()
        pwm = self.servo.pwm
        self.servo.mover = Mock(side_effect=KeyboardInterrupt)
        with self.assertRaises(KeyboardInterrupt):
            self.servo.ejecutar(((800, 600), (1850, 600)))
        self.servo.mover.assert_called_once_with(800, 600)
        pwm.deinit.assert_called_once()
        self.assertIsNone(self.servo.pwm)

    def test_limites_y_sentido_inverso(self):
        for bad in (799, 1851, 3000, True, 800.5):
            with self.assertRaises(ValueError):
                self.servo.validar(bad)
        self.assertEqual(self.mod.secuencia_cierre(1850, 800),
                         ((800, 350), (950, 250), (800, 500)))

    def test_ajuste_invalido_no_cambia_posiciones(self):
        with patch('builtins.input', side_effect=['900', '3000']):
            with self.assertRaises(ValueError):
                self.servo.ajustar()
        self.assertEqual((self.servo.abierto, self.servo.cerrado), (800, 1850))


if __name__ == '__main__':
    unittest.main()
