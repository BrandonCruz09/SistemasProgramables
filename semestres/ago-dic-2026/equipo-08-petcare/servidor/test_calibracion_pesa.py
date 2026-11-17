# Sistemas Programables | PetCare | Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez.
# Objetivo: comprobar persistencia, conversion y fallos de la pesa en PC.
# Pines simulados: HX711 DT19/SCK18; no acciona hardware.
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

FW = Path(__file__).resolve().parents[1] / 'firmware' / 'esp32'
sys.path.insert(0, str(FW))
from calibracion_pesa import cargar
import config
import sensores


class CalibracionTests(unittest.TestCase):
    def setUp(self):
        for name, value in (('ticks_ms', lambda: 0), ('ticks_diff', lambda a,b:a-b)):
            p = patch.object(sensores.time, name, value, create=True)
            p.start(); self.addCleanup(p.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.cal = {'TARE_RAW': 1000, 'CALIBRATION_FACTOR': 20,
                    'referencia_aproximada': True, 'masa_referencia_g': 163}
        self.write('calibracion_pesa_prueba.json', self.cal)

    def write(self, name, value):
        (self.folder / name).write_text(json.dumps(value), encoding='utf-8')

    def test_tara_reciente_prevalece_al_reiniciar(self):
        self.write('tara_tazon.json', {'TARE_RAW': 1200})
        result = cargar(self.folder.as_posix())
        self.assertEqual(result['tara'], 1200)
        self.assertEqual(result['factor'], 20)

    def test_tara_original_sin_reajuste(self):
        self.assertEqual(cargar(self.folder.as_posix())['tara'], 1000)

    def test_factor_invalido_bloquea_gramos(self):
        for value in [0, None, True, '20', float('nan'), float('inf')]:
            self.write('calibracion_pesa_prueba.json', dict(self.cal, CALIBRATION_FACTOR=value))
            result = cargar(self.folder.as_posix())
            self.assertIsNone(result['factor'])
            self.assertIsNone(result['tara'])

    def test_tara_corrupta_no_reutiliza_cero_antiguo(self):
        (self.folder/'tara_tazon.json').write_text('{')
        self.assertIsNone(cargar(self.folder.as_posix())['factor'])

    def test_permite_factor_negativo(self):
        self.write('calibracion_pesa_prueba.json', dict(self.cal, CALIBRATION_FACTOR=-20))
        self.assertEqual(cargar(self.folder.as_posix())['factor'], -20)

    def test_archivos_del_montaje_validado(self):
        result = cargar(FW.as_posix())
        self.assertIsNone(result['error'])
        self.assertAlmostEqual(result['tara'], -409450.7, places=2)
        self.assertTrue(result['aproximada'])

    def hub(self, raw):
        hub = sensores.SensorHub.__new__(sensores.SensorHub)
        hub._last_poll = None
        hub._last_dht = -2500
        hub._dht_error = hub._hx_error = None
        hub._dht_last_ok = hub._weight_last_ok = None
        hub._dht_failures = 0
        hub._now = 0
        hub._temperature = hub._humidity = hub._weight = hub._raw = None
        hub._dht_ok = hub._hx_ok = False
        hub._dht = types.SimpleNamespace(measure=lambda: None, temperature=lambda: 25, humidity=lambda: 50)
        hub._pir = types.SimpleNamespace(value=lambda: 0)
        hub._float = None
        hub._hx = types.SimpleNamespace(read_average=lambda *a, **k: raw)
        return hub

    def test_sensor_publica_gramos_y_conserva_signo(self):
        with patch.object(config, 'TARE_RAW', 1000), patch.object(config, 'CALIBRATION_FACTOR', 20):
            for raw, expected in [(1000, 0), (4260, 163), (980, -1)]:
                result = self.hub(raw).read(0)
                self.assertEqual(result['weight_g'], expected)
                self.assertEqual(result['weight_unit'], 'g')
                self.assertIsNone(result['water_available'])

    def test_fallo_hx_no_publica_ultimo_peso_como_valido(self):
        hub = self.hub(4260)
        hub._weight = 163
        def fail(*a, **k): raise TimeoutError('HX desconectado')
        hub._hx.read_average = fail
        result = hub.read(0)
        self.assertIsNone(result['weight_g'])
        self.assertFalse(result['hx_ok'])


if __name__ == '__main__':
    unittest.main()
