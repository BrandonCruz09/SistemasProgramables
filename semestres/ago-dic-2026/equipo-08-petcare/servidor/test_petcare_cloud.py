# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: test_petcare_cloud.py
# Objetivo: Validar lógica con dobles de prueba; no sustituye pruebas físicas.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica: ejecutado en PC.
# ============================================
# Pruebas unitarias sin ESP32, broker MQTT ni cuenta Firebase.
import unittest
from petcare_server import movement_detected, sanitize_command


class PetCareCloudTests(unittest.TestCase):
    def test_accepts_only_known_command_with_id(self):
        self.assertEqual(sanitize_command({"id": "orden-1", "action": "feed"}),
                         ("orden-1", "feed"))
        self.assertEqual(sanitize_command({"id": "orden-2", "action": "water"}),
                         ("orden-2", "water"))
        self.assertEqual(sanitize_command({"id": "orden-3", "action": "stop_water"}),
                         ("orden-3", "stop_water"))
        self.assertIsNone(sanitize_command({"id": "orden-4", "action": "servo_180"}))
        self.assertIsNone(sanitize_command({"action": "feed"}))
        self.assertIsNone(sanitize_command(None))

    def test_motion_threshold(self):
        self.assertFalse(movement_detected(0))
        self.assertFalse(movement_detected(1.79))
        self.assertTrue(movement_detected(1.8))
        self.assertFalse(movement_detected("no numerico"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
