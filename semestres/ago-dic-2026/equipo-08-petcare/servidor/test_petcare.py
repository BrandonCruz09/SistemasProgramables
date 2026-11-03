# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: test_petcare.py
# Objetivo: Validar lógica con dobles de prueba; no sustituye pruebas físicas.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica: ejecutado en PC.
# ============================================
# Pruebas de logica para Windows/macOS/Linux: python test_petcare.py
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "firmware" / "esp32"))
import config
from controlador import PetCareController

class FakeSensors:
    def __init__(self, calibrated=True, weight=0, water=True):
        self.calibrated = calibrated
        self.weight = weight
        self.water = water
    def read(self, _now):
        return {"calibrated": self.calibrated, "weight_g": self.weight,
                "water_available": self.water, "pir": False}

class FakeServo:
    def __init__(self): self.angles=[]; self.released=0
    def move_to(self, angle): self.angles.append(angle)
    def release(self): self.released += 1

class FakePump:
    def __init__(self): self.active=False
    def on(self): self.active=True
    def off(self): self.active=False

class FakeBuzzer:
    def __init__(self): self.active=False
    def on(self): self.active=True
    def off(self): self.active=False

class FakeLed:
    def __init__(self): self.color=None
    def set_color(self, color): self.color=color

class PetCareTests(unittest.TestCase):
    def make_controller(self, **kwargs):
        self.servo=FakeServo(); self.pump=FakePump(); self.buzzer=FakeBuzzer(); self.led=FakeLed()
        self.controller=PetCareController(FakeSensors(**kwargs), self.servo, self.pump, self.buzzer, self.led)
        return self.controller

    def test_feed_requires_calibrated_scale(self):
        c=self.make_controller(calibrated=False, weight=None)
        c.tick(0)
        ok, _=c.request_feed(0)
        self.assertFalse(ok)
        self.assertEqual(self.servo.angles, [])

    def test_feed_opens_closes_and_releases_pwm(self):
        c=self.make_controller()
        c.tick(0)
        ok, _=c.request_feed(0)
        self.assertTrue(ok)
        c.tick(config.SERVO_OPEN_TIME_MS)
        self.assertEqual(self.servo.angles, [config.SERVO_OPEN_ANGLE, config.SERVO_CLOSED_ANGLE])
        c.tick(config.SERVO_OPEN_TIME_MS + config.SERVO_SETTLE_MS)
        self.assertEqual(c.state, c.IDLE)
        self.assertGreaterEqual(self.servo.released, 1)

    def test_bowl_weight_blocks_extra_food(self):
        c=self.make_controller(weight=config.BOWL_MAX_WEIGHT_G)
        c.tick(0)
        ok, _=c.request_feed(0)
        self.assertFalse(ok)

    def test_pump_is_interlocked_and_times_out(self):
        c=self.make_controller()
        c.tick(0)
        ok, _=c.request_pump(0)
        self.assertTrue(ok); self.assertTrue(self.pump.active)
        c.tick(config.PUMP_PULSE_MS)
        self.assertFalse(self.pump.active); self.assertEqual(c.state, c.IDLE)

    def test_empty_water_blocks_pump(self):
        c=self.make_controller(water=False)
        c.tick(0)
        ok, _=c.request_pump(0)
        self.assertFalse(ok); self.assertFalse(self.pump.active)

if __name__ == "__main__":
    unittest.main(verbosity=2)
