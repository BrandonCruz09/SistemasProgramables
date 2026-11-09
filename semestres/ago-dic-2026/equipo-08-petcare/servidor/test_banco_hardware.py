# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: test_banco_hardware.py
# Objetivo: Verificar que las pruebas apagan salidas al terminar o interrumpirse.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: Simulados en PC; bomba23 y servo33.
# ============================================
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BENCH = Path(__file__).resolve().parents[1] / 'firmware' / 'pruebas'


class Pin:
    OUT = 1

    def __init__(self, gpio, mode, value=0):
        self.gpio = gpio
        self.values = [value]

    def value(self, value):
        self.values.append(value)


def load(name):
    spec = importlib.util.spec_from_file_location(name, BENCH / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'machine': types.SimpleNamespace(Pin=Pin, PWM=None)}):
        spec.loader.exec_module(module)
    return module


class BancoTests(unittest.TestCase):
    def test_bomba_termina_apagada(self):
        module = load('prueba_bomba_gpio23')
        bomba = module.BombaPrueba()
        with patch.object(module, 'esperar'):
            bomba.pulso(800)
        self.assertEqual(bomba.salida.values, [0, 1, 0])

    def test_interrupcion_apaga_bomba(self):
        module = load('prueba_bomba_gpio23')
        bomba = module.BombaPrueba()
        with patch.object(module, 'esperar', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                bomba.pulso(800)
        self.assertEqual(bomba.salida.values[-1], 0)

    def test_duracion_invalida_no_activa(self):
        module = load('prueba_bomba_gpio23')
        bomba = module.BombaPrueba()
        for duracion in (-1, 0, 1001):
            with self.assertRaises(ValueError):
                bomba.pulso(duracion)
        self.assertEqual(bomba.salida.values, [0])

    def test_servo_rechaza_pulso_fuera_de_limite(self):
        module = load('identificar_giro_gpio33')
        pwm = types.SimpleNamespace(duty_u16=lambda _: self.fail('No debe emitir PWM'))
        for pulso in (800, 3000):
            with self.assertRaises(ValueError):
                module.escribir_pulso(pwm, pulso)


if __name__ == '__main__':
    unittest.main()
