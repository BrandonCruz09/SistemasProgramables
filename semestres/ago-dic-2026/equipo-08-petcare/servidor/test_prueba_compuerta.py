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
        self.servo.ciclo(con_alivio=True)
        self.hardware.PWM.assert_not_called()

    def test_ciclo_limitado_mantiene_posicion(self):
        self.servo.ajustes_confirmados = True
        self.servo.mover = Mock()
        self.servo.ciclo()
        self.assertEqual([c.args for c in self.servo.mover.call_args_list],
                         [(1390, 900), (1690, 3000)])
        self.pin.value.assert_not_called()

    def test_apertura_1390_conserva_pwm_despues_de_600_ms(self):
        reloj = types.SimpleNamespace(ticks_ms=Mock(side_effect=[0, 0, 600]),
                                      ticks_diff=lambda a, b: a-b, sleep_ms=Mock())
        with patch.object(self.mod, 'time', reloj):
            self.servo.ejecutar(((1390, self.mod.ESPERA_APERTURA_MS),))
        pwm = self.hardware.PWM.return_value
        self.assertEqual(self.hardware.PWM.call_args.kwargs['duty_ns'], 1390000)
        pwm.duty_ns.assert_called_with(1390000)
        pwm.deinit.assert_not_called()
        self.servo.liberar()
        pwm.deinit.assert_called_once()

    def test_alivio_solo_por_opcion_explicita(self):
        self.servo.ajustes_confirmados = True
        self.servo.mover = Mock()
        self.servo.ciclo(con_alivio=True)
        self.assertEqual([c.args for c in self.servo.mover.call_args_list],
                         [(1390, 900), (1690, 350), (1590, 250), (1690, 500)])

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
        for bad in (800, 1299, 1851, 3000, True, 1390.5):
            with self.assertRaises(ValueError):
                self.servo.validar(bad)
        self.assertEqual(self.mod.secuencia_cierre(1850, 1600),
                         ((1600, 350), (1683, 250), (1600, 500)))

    def test_ajuste_invalido_no_cambia_posiciones(self):
        with patch('builtins.input', side_effect=['900', '3000']):
            with self.assertRaises(ValueError):
                self.servo.ajustar()
        self.assertEqual((self.servo.abierto, self.servo.cerrado), (1390, 1690))


if __name__ == '__main__':
    unittest.main()
