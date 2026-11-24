# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Comprobar mediante pruebas de software el módulo recuperacion de PetCare.

import sys
import types
import unittest
from unittest.mock import Mock, patch
import test_petcare
import config
import sensores
from actuadores import ServoSG90


class RecuperacionTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        for target, name, value in (
                (config, 'SERVO_MOVEMENT_ENABLED', True),
                (config, 'CALIBRATION_FACTOR', 285.80386),
                (config, 'TARE_RAW', -409450.7),
                (sensores.time, 'ticks_ms', lambda: self.now),
                (sensores.time, 'ticks_diff', lambda a, b: a-b)):
            p = patch.object(target, name, value, create=True)
            p.start(); self.addCleanup(p.stop)

    def hub(self, measurements):
        dht_sensor = Mock()
        dht_sensor.measure.side_effect = measurements
        dht_sensor.temperature.return_value = 23.5
        dht_sensor.humidity.return_value = 60.0
        pin = Mock(); pin.return_value.value.return_value = 0
        hx = Mock(); hx.read_average.return_value = config.TARE_RAW
        p = patch.dict(sys.modules, {'machine': types.SimpleNamespace(Pin=pin),
                                     'dht': types.SimpleNamespace(DHT22=Mock(return_value=dht_sensor))})
        p.start(); self.addCleanup(p.stop)
        p = patch.object(sensores, 'HX711', return_value=hx)
        p.start(); self.addCleanup(p.stop)
        return sensores.SensorHub(), dht_sensor, hx

    def test_dht_espera_recupera_y_no_muestra_datos_viejos(self):
        hub, dht_sensor, hx = self.hub([None, OSError(116), None])
        self.assertIsNone(hub.read(0)['temperature_c'])
        dht_sensor.measure.assert_not_called()
        self.now = 2500
        self.assertTrue(hub.read(self.now)['dht_ok'])
        self.now = 5000
        failed = hub.read(self.now)
        self.assertFalse(failed['dht_ok'])
        self.assertIsNone(failed['temperature_c'])
        self.assertIn('116', failed['dht_error'])
        self.assertTrue(failed['hx_ok'])
        self.assertEqual(failed['weight_g'], 0)
        self.now = 7500
        self.assertTrue(hub.read(self.now)['dht_ok'])

    def test_hx_falla_y_recupera_sin_cambiar_calibracion(self):
        hub, _, hx = self.hub([None, None])
        hx.read_average.side_effect = [TimeoutError('DT'), config.TARE_RAW + config.CALIBRATION_FACTOR*163]
        self.assertFalse(hub.read(0)['hx_ok'])
        self.now = 2500
        recovered = hub.read(self.now)
        self.assertAlmostEqual(recovered['weight_g'], 163)
        self.assertEqual(config.TARE_RAW, -409450.7)
        self.assertEqual(config.CALIBRATION_FACTOR, 285.80386)

    def controller(self):
        c = test_petcare.PetCareTests().make_controller()
        c.tick(0)
        return c

    def test_no_lecturas_bloqueantes_durante_apertura_ni_cierre(self):
        c = self.controller()
        c.request_feed(0)
        c.sensors.read = Mock(side_effect=OSError('sensor lento'))
        c.tick(900)
        self.assertEqual(c.servo.angles, [850,1500])
        c.sensors.read.assert_not_called()
        c.tick(1250)
        self.assertFalse(c.status['hx_ok'])

    def test_servo_fallido_bloquea_otro_intento_y_bomba(self):
        c = self.controller()
        c.servo.move_us = Mock(side_effect=RuntimeError('PWM is inactive'))
        self.assertFalse(c.request_feed(0)[0])
        self.assertEqual(c.state, c.FAULT)
        self.assertFalse(c.request_pump(100)[0])
        self.assertFalse(c.request_feed(100)[0])
        self.assertEqual(c.servo.move_us.call_count, 1)

    def test_parada_no_ordena_otro_movimiento_y_limpia_si_buzzer_falla(self):
        c = self.controller(); c.request_feed(0)
        c.buzzer.off = Mock(side_effect=OSError('buzzer'))
        c.safe_shutdown()
        self.assertEqual(c.servo.angles, [850])
        self.assertEqual(c.servo.released, 1)
        self.assertFalse(c.pump.active)

    def test_peso_viejo_o_invalido_bloquea_dispensa(self):
        for value in (None, float('nan'), float('inf'), True):
            c = self.controller(); c.status['weight_g'] = value
            self.assertFalse(c.request_feed(0)[0])
        c = self.controller()
        self.assertFalse(c.request_feed(4000)[0])
        c = self.controller(); c.status['hx_ok'] = False
        self.assertFalse(c.request_feed(0)[0])

    def test_pwm_error_libera_sin_reintentar(self):
        pwm = Mock(); pwm.duty_ns.side_effect = RuntimeError('inactive')
        pin = Mock()
        with patch.dict(sys.modules, {'machine': types.SimpleNamespace(Pin=Mock(return_value=pin), PWM=Mock(return_value=pwm))}):
            servo = ServoSG90()
            with self.assertRaises(RuntimeError): servo.move_us(1400)
            pwm.deinit.assert_called_once()
            self.assertIsNone(servo._pwm)
            self.assertEqual(pin.value.call_args.args, (0,))

    def test_rechaza_posiciones_anteriores_peligrosas(self):
        with patch.dict(sys.modules, {'machine': types.SimpleNamespace(Pin=Mock(), PWM=Mock())}):
            servo = ServoSG90()
            for value in (800,849,1501,1700,3000):
                with self.assertRaises(ValueError): servo.move_us(value)


if __name__ == '__main__': unittest.main()
