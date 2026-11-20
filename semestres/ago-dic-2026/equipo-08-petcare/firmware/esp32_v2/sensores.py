"""Sensores independientes; conserva RAW y no cambia tara al arrancar."""

import time
import config
from calibracion_pesa import cargar


class SensorHub:
    def __init__(self):
        from machine import Pin
        from hx711 import HX711
        import dht

        self.cal = cargar()
        self.hx = self.dht = self.pir = None
        self.errors = {}
        for name, factory in (
            ("hx", lambda: HX711(config.PIN_HX711_DOUT, config.PIN_HX711_SCK)),
            ("dht", lambda: dht.DHT22(Pin(config.PIN_DHT22, Pin.IN, Pin.PULL_UP))),
            ("pir", lambda: Pin(config.PIN_PIR, Pin.IN, Pin.PULL_DOWN)),
        ):
            try:
                setattr(self, name, factory())
            except Exception as exc:
                self.errors[name] = repr(exc)
        self.samples = []
        self.raw = self.last_hx = self.last_dht = None
        self.temp = self.humidity = None
        self.next_dht = time.ticks_add(time.ticks_ms(), 2500)
        self.started = time.ticks_ms()

    def read(self, now_ms=None, slow=True):
        now = time.ticks_ms() if now_ms is None else now_ms
        if self.hx is not None:
            try:
                raw = self.hx.read_ready()
                if raw is not None:
                    self.raw = raw
                    self.samples.append(raw)
                    self.samples = self.samples[-5:]
                    self.last_hx = time.ticks_ms()
                    self.errors.pop("hx", None)
            except Exception as exc:
                self.errors["hx"] = repr(exc)
                self.samples = []
        if slow and self.dht is not None and time.ticks_diff(now, self.next_dht) >= 0:
            self.next_dht = time.ticks_add(now, 2500)
            try:
                self.dht.measure()
                t, h = self.dht.temperature(), self.dht.humidity()
                if not -40 <= t <= 80 or not 0 <= h <= 100:
                    raise ValueError("DHT fuera de rango")
                self.temp, self.humidity = t, h
                self.last_dht = time.ticks_ms()
                self.errors.pop("dht", None)
            except Exception as exc:
                self.temp = self.humidity = None
                self.errors["dht"] = repr(exc)
        return self.snapshot(time.ticks_ms())

    def snapshot(self, now):
        age = time.ticks_diff(now, self.last_hx) if self.last_hx is not None else None
        valid = age is not None and age <= config.WEIGHT_MAX_AGE_MS and "hx" not in self.errors
        calibrated = self.cal["error"] is None
        weight = control = span = None
        if valid and calibrated and self.samples:
            ordered = sorted(self.samples)
            weight = (ordered[len(ordered) // 2] - self.cal["tara"]) / self.cal["factor"]
            control = (self.raw - self.cal["tara"]) / self.cal["factor"]
            span = (max(ordered) - min(ordered)) / abs(self.cal["factor"])
        pir = None
        try:
            if self.pir is not None:
                pir = bool(self.pir.value())
        except Exception as exc:
            self.errors["pir"] = repr(exc)
        return {
            "raw": self.raw,
            "weight_g": weight,
            "weight_control_g": control,
            "weight_unit": "g",
            "weight_age_ms": age,
            "weight_span_g": span,
            "hx_ok": valid,
            "hx_error": (
                self.errors.get("hx") if valid else self.errors.get("hx", "Esperando HX711")
            ),
            "calibrated": calibrated,
            "calibration_error": self.cal["error"],
            "calibration_approximate": self.cal["aproximada"],
            "calibration_reference_g": self.cal["referencia_g"],
            "tare_raw": self.cal["tara"],
            "calibration_factor": self.cal["factor"],
            "calibration_file": self.cal["archivo"],
            "pir": pir,
            "temperature_c": self.temp,
            "humidity_pct": self.humidity,
            "dht_ok": self.temp is not None and "dht" not in self.errors,
            "dht_error": self.errors.get("dht"),
            "water_available": None,
            "water_level_monitored": False,
            "readings_paused": False,
        }
