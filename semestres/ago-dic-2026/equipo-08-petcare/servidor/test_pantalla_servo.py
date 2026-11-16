# Sistemas Programables | PetCare | Equipo 08
# Pruebas en PC de pulsos, pantalla y pines. No accionan hardware.
import math
import sys
import types
import unittest
from unittest.mock import Mock, patch
import test_petcare
import config
from actuadores import ServoSG90
from pantalla_peso import PantallaPeso, texto_peso


class MontajeTests(unittest.TestCase):
    def test_pulsos_de_compuerta_y_rechazo_de_3000(self):
        pin = Mock(); pwm = Mock()
        pin_cls = Mock(return_value=pin)
        pwm_cls = Mock(return_value=pwm)
        with patch.dict(sys.modules, {'machine': types.SimpleNamespace(Pin=pin_cls, PWM=pwm_cls)}):
            servo = ServoSG90()
            servo.move_us(config.SERVO_CLOSED_US)
            self.assertEqual(pwm.duty_ns.call_args.args, (1850000,))
            servo.move_us(config.SERVO_OPEN_US)
            self.assertEqual(pwm.duty_ns.call_args.args, (800000,))
            for bad in (3000, 799, True, float('nan')):
                with self.assertRaises(ValueError): servo.move_us(bad)
            servo.release(); pwm.deinit.assert_called_once()
            self.assertEqual(pin.value.call_args.args, (0,))

    def test_ciclo_controlador_usa_posiciones_observadas(self):
        c = test_petcare.PetCareTests().make_controller()
        c.tick(0); c.request_feed(0)
        c.tick(config.SERVO_OPEN_TIME_MS)
        self.assertEqual(c.servo.angles, [800, 1850])
        c.tick(config.SERVO_OPEN_TIME_MS + config.SERVO_SETTLE_MS)
        self.assertEqual(c.state, 'LISTO')

    def test_pantalla_no_inventa_cero_ni_oculta_negativos(self):
        status = {'calibrated':True, 'hx_ok':True, 'weight_g':163.2}
        self.assertEqual(texto_peso(status), '163.2 g')
        self.assertEqual(texto_peso(dict(status, weight_g=-1.2)), '-1.2 g')
        for bad in (None, float('nan'), float('inf'), True):
            self.assertEqual(texto_peso(dict(status, weight_g=bad)), 'SIN LECTURA')
        self.assertEqual(texto_peso(dict(status,hx_ok=False)), 'SIN LECTURA')
        self.assertEqual(texto_peso(dict(status,calibrated=False)), 'SIN CALIBRAR')

    def test_oled_ausente_no_detiene_proyecto(self):
        bus = Mock(); bus.scan.return_value = []
        with patch.dict(sys.modules, {'machine':types.SimpleNamespace(Pin=Mock(), SoftI2C=Mock(return_value=bus)),
                                      'ssd1306':types.SimpleNamespace(SSD1306_I2C=Mock())}):
            screen = PantallaPeso()
            self.assertIsNone(screen.oled)
            screen.update({}, 'LISTO', 0)

    def test_fallo_i2c_desactiva_solo_pantalla(self):
        screen = PantallaPeso.__new__(PantallaPeso)
        screen.oled = Mock(); screen.oled.fill.side_effect = OSError('I2C')
        screen.last_update = None
        screen.update({}, 'LISTO', 0)
        self.assertIsNone(screen.oled)

    def test_pines_oled_no_chocan_con_componentes(self):
        active = [config.PIN_DHT22,config.PIN_PIR,config.PIN_HX711_DOUT,config.PIN_HX711_SCK,
                  config.PIN_SERVO,config.PIN_PUMP_RELAY,config.PIN_BUZZER,
                  config.PIN_LED_R,config.PIN_LED_G,config.PIN_LED_B,
                  config.OLED_SDA,config.OLED_SCL]
        self.assertEqual(len(active),len(set(active)))
        self.assertEqual((config.OLED_SDA,config.OLED_SCL),(26,25))


if __name__ == '__main__': unittest.main()
