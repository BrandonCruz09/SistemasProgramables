import sys, types, time, json, tempfile, unittest, hashlib
from pathlib import Path

ROOT = Path(__file__).parent
FW = ROOT.parent
sys.path.insert(0, str(FW))
clock = [0]
time.ticks_ms = lambda: clock[0]
time.ticks_add = lambda a, b: (a + b) % (1 << 30)
time.ticks_diff = lambda a, b: ((a - b + (1 << 29)) % (1 << 30)) - (1 << 29)
time.sleep_us = lambda n: None
time.sleep_ms = lambda n: clock.__setitem__(0, time.ticks_add(clock[0], n))


class Pin:
    IN = 0
    OUT = 1
    PULL_UP = 2
    PULL_DOWN = 3

    def __init__(self, n, *args, **kw):
        self.n = n
        self.v = kw.get("value", 0)
        self.writes = []

    def value(self, v=None):
        if v is not None:
            self.v = v
            self.writes.append(v)
        return self.v


class PWM:
    def __init__(self, pin, **kw):
        self.pin = pin
        self.f = kw["freq"]
        self.ns = kw.get("duty_ns")
        self.active = True

    def freq(self, value=None):
        if value is not None:
            self.f = value
        return self.f

    def duty_u16(self, value):
        self.duty = value

    def duty_ns(self, n=None):
        if n is not None:
            self.ns = n
        return self.ns

    def deinit(self):
        self.active = False


class Timer:
    ONE_SHOT = 0

    def __init__(self, n):
        self.callback = None

    def init(self, **kw):
        self.callback = kw["callback"]
        self.period = kw["period"]

    def deinit(self):
        self.callback = None


machine = types.ModuleType("machine")
machine.Pin = Pin
machine.PWM = PWM
machine.Timer = Timer
machine.disable_irq = lambda: 0
machine.enable_irq = lambda n: None
sys.modules["machine"] = machine
sys.modules["binascii"] = __import__("binascii")
import config
from actuadores import ServoSG90, PumpRelay, ActiveBuzzer
from controlador import PetCareController
from calibracion_pesa import cargar
from mqtt_link import packet, take_packet, MQTTLink, string
from hx711 import HX711


class Sensor:
    def __init__(self):
        self.g = 0
        self.valid = True
        self.dht = False

    def read(self, now, slow=True):
        return dict(
            weight_g=self.g,
            weight_control_g=self.g,
            weight_age_ms=0,
            calibrated=True,
            hx_ok=self.valid,
            dht_ok=self.dht,
        )


class Tests(unittest.TestCase):
    def setUp(self):
        clock[0] = 1000
        self.s = Sensor()
        self.v = ServoSG90()
        self.p = PumpRelay()
        self.b = ActiveBuzzer()
        self.c = PetCareController(self.s, self.v, self.p, self.b)
        self.c.tick(clock[0])

    def tick(self, ms):
        clock[0] = time.ticks_add(clock[0], ms)
        return self.c.tick(clock[0])

    def test_pin_map(self):
        self.assertEqual(
            (
                config.PIN_SERVO,
                config.PIN_PUMP_RELAY,
                config.PIN_BUZZER,
                config.PIN_DHT22,
                config.PIN_PIR,
                config.PIN_HX711_DOUT,
                config.PIN_HX711_SCK,
                config.OLED_SDA,
                config.OLED_SCL,
            ),
            (33, 23, 22, 4, 27, 19, 18, 26, 25),
        )

    def test_boot_does_not_move(self):
        self.assertIsNone(self.v.pwm)
        self.assertEqual(self.p.pin.value(), 1)

    def test_servo_exact_pulses_hold(self):
        self.assertTrue(self.c.request_gate(True, 1000)[0])
        p = self.v.pwm
        self.tick(600)
        self.assertIs(self.v.pwm, p)
        self.assertEqual(p.ns, 1350000)
        self.c.request_gate(False, 1600)
        self.assertEqual(p.ns, 1690000)
        self.assertTrue(p.active)

    def test_never_800_or_3000(self):
        for x in (800, 3000, 1390, True):
            with self.assertRaises(ValueError):
                self.v.move_us(x)

    def test_dry_gate_ignores_bad_scale_and_holds(self):
        self.s.g = 1470
        self.s.valid = False
        self.tick(1)
        self.assertTrue(self.c.command("gate_test_open", 1001)[0])
        self.tick(120000)
        self.assertEqual(self.v.pulse, 1350)
        self.assertTrue(self.c.gate_test_open)
        self.assertFalse(self.c.request_food(clock[0])[0])
        self.assertTrue(self.c.command("gate_close", clock[0])[0])
        self.assertEqual(self.v.pulse, 1690)
        self.assertFalse(self.c.gate_test_open)

    def test_manual_closes_at_300(self):
        self.c.request_gate(True, 1000)
        self.s.g = 299
        self.tick(10)
        self.assertEqual(self.v.pulse, 1350)
        self.s.g = 300
        self.tick(10)
        self.assertEqual(self.v.pulse, 1690)
        self.assertIsNone(self.c.food_mode)

    def test_feed_batch_then_target(self):
        self.assertTrue(self.c.request_food(1000)[0])
        self.tick(1)
        self.assertEqual(self.v.pulse, 1350)
        self.tick(250)
        self.assertEqual(self.v.pulse, 1690)
        self.s.g = 301
        self.tick(1200)
        self.assertIsNone(self.c.food_mode)

    def test_no_progress_closes(self):
        self.c.request_food(1000)
        for _ in range(12):
            self.tick(1300)
        self.assertIsNone(self.c.food_mode)
        self.assertEqual(self.v.pulse, 1690)

    def test_sensor_lost_closes(self):
        self.c.request_gate(True, 1000)
        self.s.valid = False
        self.tick(10)
        self.assertEqual(self.v.pulse, 1690)

    def test_close_works_with_bad_weight(self):
        self.s.valid = False
        self.tick(1)
        self.assertTrue(self.c.request_gate(False, 1001)[0])

    def test_bad_weight_no_auto_feed(self):
        self.s.valid = False
        self.tick(1)
        self.assertFalse(self.c.request_food(1001)[0])

    def test_water_exact_deadline(self):
        self.assertTrue(self.c.request_pump(1000)[0])
        self.assertEqual(self.p.pin.value(), 0)
        self.tick(4999)
        self.assertTrue(self.p.active)
        self.tick(1)
        self.assertFalse(self.p.active)
        self.assertEqual(self.p.pin.value(), 1)
        self.assertEqual(self.c.water_events[-1]["duration_ms"], 5000)

    def test_timer_independent_cutoff(self):
        self.p.on()
        self.p.timer.callback(None)
        self.assertFalse(self.p.active)
        self.assertEqual(self.p.pin.value(), 1)

    def test_water_does_not_move_servo(self):
        self.c.request_gate(False, 1000)
        p = self.v.pwm
        self.c.request_pump(1000)
        self.tick(5000)
        self.assertIs(self.v.pwm, p)
        self.assertEqual(p.ns, 1690000)
        self.assertEqual(p.f, 50)

    def test_no_overlap_water_food(self):
        self.c.request_gate(True, 1000)
        self.assertFalse(self.c.request_pump(1000)[0])

    def test_buzzer_stops_and_no_pwm_change(self):
        self.v.move_us(1690)
        self.c.request_beep(1000, "passive")
        self.assertEqual(self.b.pwm.freq(), 1000)
        self.assertEqual(self.v.pwm.freq(), 50)
        self.tick(2000)
        self.assertIsNone(self.b.pwm)
        self.assertEqual(self.v.pwm.duty_ns(), 1690000)

    def test_two_notes_do_not_change_servo(self):
        self.v.move_us(1690)
        self.c.request_beep(1000, "passive")
        self.tick(700)
        self.assertEqual(self.b.pwm.duty, 0)
        self.tick(200)
        self.assertEqual(self.b.pwm.freq(), 1500)
        self.assertEqual(self.b.pwm.duty, 32768)
        self.assertEqual(self.v.pwm.freq(), 50)
        self.assertEqual(self.v.pulse, 1690)
        self.tick(1100)
        self.assertIsNone(self.b.pwm)

    def test_dht_failure_not_blocks_water(self):
        self.assertFalse(self.c.status["dht_ok"])
        self.assertTrue(self.c.request_pump(1000)[0])

    def test_shutdown(self):
        self.p.on()
        self.b.on()
        self.v.move_us(1690)
        self.c.safe_shutdown()
        self.assertFalse(self.p.active)
        self.assertIsNone(self.v.pwm)
        self.assertEqual(self.b.pin.value(), 0)

    def test_saved_calibration_no_mutation(self):
        p = FW / "calibracion_validada.json"
        before = p.read_bytes()
        for _ in range(5):
            c = cargar(str(FW))
            self.assertEqual(c["factor"], 285.80386)
            self.assertEqual(c["tara"], -428929.16)
        self.assertEqual(before, p.read_bytes())

    def test_newer_tare_does_not_override(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "calibracion_validada.json").write_bytes(
                (FW / "calibracion_validada.json").read_bytes()
            )
            Path(folder, "tara_tazon.json").write_text('{"TARE_RAW":0}')
            self.assertEqual(cargar(folder)["tara"], -428929.16)

    def test_missing_calibration_not_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            c = cargar(folder)
            self.assertIsNone(c["factor"])
            self.assertIsNotNone(c["error"])

    def test_mqtt_partial_packet_nonblocking(self):
        p = packet(0x30, b"a" * 300)
        b = bytearray()
        for v in p[:-1]:
            b.append(v)
            self.assertIsNone(take_packet(b))
        b.append(p[-1])
        self.assertEqual(take_packet(b), (0x30, b"a" * 300, len(p)))

    def test_mqtt_bad_length(self):
        with self.assertRaises(ValueError):
            take_packet(bytearray(b"\x30\xff\xff\xff\xff"))

    def test_mqtt_retained_command_ignored(self):
        m = MQTTLink()
        m.receive(
            0x31,
            string(m.base + "/commands")
            + json.dumps(
                {"id": "1", "action": "gate_close", "session_id": self.c.session}
            ).encode(),
            self.c,
            1000,
        )
        self.assertIsNone(self.v.pwm)

    def test_mqtt_duplicate_not_reexecuted(self):
        m = MQTTLink()
        d = {"id": "1", "action": "water", "supervised": True, "session_id": self.c.session}
        body = string(m.base + "/commands") + json.dumps(d).encode()
        m.receive(0x30, body, self.c, 1000)
        m.receive(0x30, body, self.c, 1000)
        self.assertEqual(self.c.water_sequence, 1)

    def test_ticks_wrap(self):
        clock[0] = (1 << 30) - 2000
        self.c.request_pump(clock[0])
        self.tick(5000)
        self.assertFalse(self.p.active)
        self.assertEqual(self.c.water_events[-1]["duration_ms"], 5000)

    def test_hx_signed_and_25_clocks(self):
        h = HX711(19, 18)
        clock[0] += 500
        bits = [0] + [(0xFFFF9C >> i) & 1 for i in range(23, -1, -1)]
        h.dout.value = lambda: bits.pop(0)
        h.sck.writes = []
        self.assertEqual(h.read_ready(), -100)
        self.assertEqual(sum(h.sck.writes), 25)
        self.assertEqual(h.sck.value(), 0)


class FaultTests(unittest.TestCase):
    setUp = Tests.setUp
    tick = Tests.tick

    def test_fault_allows_network_recovery_without_restarting_food(self):
        self.c.handle_fault(OSError("control"), 1000)
        self.assertFalse(self.c.action_in_progress())
        self.assertFalse(self.c.request_food(1000)[0])
        self.assertFalse(self.c.request_pump(1000)[0])
        self.assertTrue(self.c.request_gate(False, 1000)[0])
        self.assertEqual(self.c.state, self.c.IDLE)

    def test_main_keeps_reading_after_network_and_display_errors(self):
        from unittest.mock import Mock, patch
        from main import main

        self.s.cal = {"factor": 285.80386, "tara": -428929.16}
        wifi = Mock()
        wifi.connected.return_value = False
        wifi.tick.side_effect = OSError("wifi")
        mqtt = Mock()
        mqtt.poll.side_effect = OSError("mqtt")
        web = Mock()
        web.poll.side_effect = OSError("panel")
        screen = Mock()
        screen.update.side_effect = OSError("oled")
        with patch("actuadores.PumpRelay", return_value=self.p), patch(
            "actuadores.ServoSG90", return_value=self.v
        ), patch("actuadores.ActiveBuzzer", return_value=self.b), patch(
            "sensores.SensorHub", return_value=self.s
        ), patch(
            "wifi_panel.Wifi", return_value=wifi
        ), patch(
            "wifi_panel.WebDashboard", return_value=web
        ), patch(
            "mqtt_link.MQTTLink", return_value=mqtt
        ), patch(
            "pantalla_peso.PantallaPeso", return_value=screen
        ), patch.object(
            self.s, "read", wraps=self.s.read
        ) as read:
            main(max_runtime_ms=30)
            self.assertGreaterEqual(read.call_count, 4)
        self.assertFalse(self.p.active)
        self.assertIsNone(self.v.pwm)
        mqtt.close.assert_called_once()
        web.close.assert_called_once()

    def test_buzzer_tick_failure_cuts_sound(self):
        from unittest.mock import patch

        self.b.on()
        with patch.object(self.b, "tick", side_effect=OSError("PWM")):
            self.tick(10)
        self.assertIsNone(self.b.pwm)
        self.assertEqual(self.c.state, self.c.FAULT)

    def test_initialization_failure_still_shuts_down_outputs(self):
        from unittest.mock import patch
        from main import main

        with patch("actuadores.PumpRelay", return_value=self.p), patch(
            "actuadores.ServoSG90", return_value=self.v
        ), patch("actuadores.ActiveBuzzer", return_value=self.b), patch(
            "sensores.SensorHub", side_effect=OSError("inicio")
        ):
            self.p.on()
            self.b.on()
            self.v.move_us(1690)
            with self.assertRaises(OSError):
                main(max_runtime_ms=20)
        self.assertFalse(self.p.active)
        self.assertIsNone(self.b.pwm)
        self.assertIsNone(self.v.pwm)

    def test_close_failure_is_not_ready(self):
        from unittest.mock import patch

        self.c.request_gate(True, 1000)
        with patch.object(self.v, "move_us", side_effect=OSError("PWM")):
            self.assertFalse(self.c.stop_food(1100)[0])
        self.assertEqual(self.c.state, self.c.FAULT)
        self.assertEqual(self.c.gate_command, "cierre_fallido")
        self.assertIsNone(self.c.food_mode)

    def test_failed_automatic_close_does_not_restart_feed(self):
        from unittest.mock import patch

        self.c.request_gate(True, 1000)
        self.s.g = 300
        with patch.object(self.v, "move_us", side_effect=OSError("PWM")) as move:
            self.tick(10)
            self.tick(10)
            self.assertEqual(move.call_count, 2)
        self.assertEqual(self.c.state, self.c.FAULT)
        self.assertFalse(self.c.request_food(clock[0])[0])

    def test_control_fault_stops_pump_and_sound(self):
        self.c.request_pump(1000)
        self.b.on()
        self.c.handle_fault(OSError("control"), 1100)
        self.assertFalse(self.p.active)
        self.assertIsNone(self.b.pwm)
        self.assertEqual(self.c.state, self.c.FAULT)
        self.assertEqual(self.c.water_events[-1]["reason"], "error_control")

    def test_fault_cleanup_continues_when_pump_stop_fails(self):
        from unittest.mock import patch

        self.b.on()
        with patch.object(self.p, "off", side_effect=OSError("pin")):
            self.c.handle_fault(OSError("control"), 1100)
        self.assertIsNone(self.b.pwm)
        self.assertIn("bomba", self.c.errors)

    def test_service_failure_does_not_stop_water_deadline(self):
        from main import run_service

        self.c.request_pump(1000)

        def broken():
            raise OSError("red")

        self.assertIsNone(run_service(self.c, "mqtt", broken))
        self.tick(5000)
        self.assertFalse(self.p.active)
        self.assertIn("servicio_mqtt", self.c.errors)
        run_service(self.c, "mqtt", lambda: True)
        self.assertNotIn("servicio_mqtt", self.c.errors)

    def test_cleanup_attempts_every_output(self):
        from main import cleanup

        calls = []

        def broken():
            calls.append("pump")
            raise OSError("pin")

        cleanup(
            [
                ("pump", broken),
                ("servo", lambda: calls.append("servo")),
                ("mqtt", lambda: calls.append("mqtt")),
            ]
        )
        self.assertEqual(calls, ["pump", "servo", "mqtt"])

    def test_invalid_buzzer_duration_does_not_energize(self):
        for duration in (None, "1000", True, -1, 3000):
            with self.assertRaises(ValueError):
                self.b.on(duration)
            self.assertIsNone(self.b.pwm)
            self.assertEqual(self.b.pin.value(), 0)

    def test_released_servo_does_not_report_stale_pulse(self):
        self.v.move_us(1690)
        self.v.release()
        self.assertIsNone(self.c.snapshot()["servo_pulse_us"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
