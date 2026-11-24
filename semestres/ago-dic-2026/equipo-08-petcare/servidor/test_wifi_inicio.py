"""Recuperacion del arranque Wi-Fi sin hardware ni credenciales."""
# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Comprobar mediante pruebas de software el módulo wifi inicio de PetCare.

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class InicioWifiTests(unittest.TestCase):
    def run_wifi(self, failures=0, connected=False, timeout=False):
        clock = [0]
        def sleep(ms): clock[0] += ms
        wlan = Mock()
        wlan.isconnected.return_value = connected
        def connect(*args):
            if wlan.connect.call_count <= failures:
                raise OSError('Wifi Internal State Error')
            wlan.isconnected.return_value = not timeout
        wlan.connect.side_effect = connect
        wlan.ifconfig.return_value = ('192.168.1.42', '', '', '')
        config = types.SimpleNamespace(WIFI_SSID='test', WIFI_PASSWORD='test',
                                       WIFI_CONNECT_TIMEOUT_MS=800, WEB_PORT=80)
        fake_time = types.SimpleNamespace(sleep_ms=sleep, ticks_ms=lambda: clock[0],
                                         ticks_diff=lambda a,b:a-b)
        path = Path(__file__).resolve().parents[1]/'firmware/esp32/wifi_panel.py'
        spec = importlib.util.spec_from_file_location('wifi_inicio_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'config':config, 'time':fake_time,
                        'network':types.SimpleNamespace(STA_IF=0, WLAN=lambda _:wlan)}):
            spec.loader.exec_module(module)
            result = module.connect_wifi()
        return result, wlan, clock[0]

    def test_recupera_error_interno(self):
        result, wlan, _ = self.run_wifi(failures=1)
        self.assertEqual(result[1], '192.168.1.42')
        self.assertEqual(wlan.connect.call_count, 2)

    def test_fallo_persistente_permite_modo_local(self):
        result, wlan, _ = self.run_wifi(failures=2)
        self.assertEqual(result, (None, None))
        self.assertEqual(wlan.active.call_args.args, (False,))

    def test_red_ausente_tiene_espera_limitada(self):
        result, wlan, elapsed = self.run_wifi(timeout=True)
        self.assertEqual(result, (None, None))
        self.assertEqual(wlan.connect.call_count, 2)
        self.assertLessEqual(elapsed, 2800)

    def test_conexion_existente_no_se_interrumpe(self):
        result, wlan, _ = self.run_wifi(connected=True)
        self.assertEqual(result[1], '192.168.1.42')
        wlan.connect.assert_not_called()
        wlan.active.assert_not_called()


if __name__ == '__main__': unittest.main()
