# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: sensores.py
# Objetivo: Leer sensores y filtrar el peso con promedio y suavizado exponencial.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo MG995=33, bomba rele=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare - lectura y filtrado ligero de sensores.
import time
import math
import config
from hx711 import HX711


class SensorHub:
    def __init__(self):
        from machine import Pin
        import dht
        self._dht = None
        self._dht_error = None
        self._dht_failures = 0
        self._dht_last_ok = None
        self._hx_error = None
        self._weight_last_ok = None
        self._now = time.ticks_ms()
        try:
            self._dht = dht.DHT22(Pin(config.PIN_DHT22, Pin.IN, Pin.PULL_UP))
        except Exception as exc:
            self._dht_error = repr(exc)
            print('DHT inicio:', self._dht_error)
        self._pir = Pin(config.PIN_PIR, Pin.IN, Pin.PULL_DOWN)
        self._float = (Pin(config.PIN_FLOAT_SWITCH, Pin.IN, Pin.PULL_UP)
                       if config.WATER_LEVEL_SENSOR_ENABLED else None)
        self._hx = None
        try:
            self._hx = HX711(config.PIN_HX711_DOUT, config.PIN_HX711_SCK)
        except Exception as exc:
            self._hx_error = repr(exc)
            print('HX711 inicio:', self._hx_error)
        self._last_poll = None
        self._last_dht = self._now
        self._temperature = None
        self._humidity = None
        self._dht_ok = False
        self._weight = None
        self._hx_ok = False
        self._raw = None

    def read(self, now_ms=None):
        if now_ms is None:
            now_ms = time.ticks_ms()
        self._now = now_ms
        if self._last_poll is not None and time.ticks_diff(now_ms, self._last_poll) < config.SENSOR_POLL_MS:
            return self._snapshot()
        self._last_poll = now_ms

        if time.ticks_diff(now_ms, self._last_dht) >= max(2500, config.DHT_POLL_MS):
            self._last_dht = now_ms
            try:
                if self._dht is None:
                    from machine import Pin
                    import dht
                    self._dht = dht.DHT22(Pin(config.PIN_DHT22, Pin.IN, Pin.PULL_UP))
                self._dht.measure()
                temperature = self._dht.temperature()
                humidity = self._dht.humidity()
                if not (-40 <= temperature <= 80 and 0 <= humidity <= 100):
                    raise ValueError('DHT fuera de rango')
                self._temperature, self._humidity = temperature, humidity
                self._dht_ok = True
                self._dht_last_ok = time.ticks_ms()
                if self._dht_failures:
                    print('DHT recuperado')
                self._dht_failures = 0
                self._dht_error = None
            except Exception as exc:
                self._dht_ok = False
                self._temperature = self._humidity = None
                self._dht_failures += 1
                self._dht_error = repr(exc)
                if self._dht_failures == 1 or self._dht_failures % 10 == 0:
                    print('DHT GPIO', config.PIN_DHT22, 'sin lectura:', self._dht_error)
                if self._dht_failures % 3 == 0:
                    self._dht = None

        try:
            if self._hx is None:
                self._hx = HX711(config.PIN_HX711_DOUT, config.PIN_HX711_SCK)
            self._raw = self._hx.read_average(3, timeout_ms=150)
            if not math.isfinite(self._raw):
                raise ValueError('HX711 lectura no finita')
            self._hx_ok = True
            self._hx_error = None
            self._weight_last_ok = time.ticks_ms()
            factor = config.CALIBRATION_FACTOR
            tare = config.TARE_RAW
            if factor not in (None, 0) and tare is not None:
                new_weight = (self._raw - tare) / factor
                # Promedio exponencial sencillo para reducir vibracion del plato.
                if self._weight is None:
                    self._weight = new_weight
                else:
                    self._weight = (0.30 * new_weight) + (0.70 * self._weight)
            else:
                self._weight = None
        except Exception as exc:
            if self._hx_error != repr(exc):
                print('HX711 sin lectura:', repr(exc))
            self._hx_error = repr(exc)
            self._hx_ok = False
            self._weight = None
            self._raw = None

        return self._snapshot()

    def _snapshot(self):
        water_level = self._float.value() if self._float is not None else None
        return {
            "pir": bool(self._pir.value()),
            "water_available": (water_level == config.FLOAT_WATER_PRESENT_LEVEL
                                if water_level is not None else None),
            "water_level_monitored": self._float is not None,
            "temperature_c": self._temperature,
            "humidity_pct": self._humidity,
            "dht_ok": self._dht_ok,
            "dht_error": self._dht_error,
            "dht_failures": self._dht_failures,
            "dht_age_ms": (max(0, time.ticks_diff(self._now, self._dht_last_ok))
                           if self._dht_last_ok is not None else None),
            "weight_g": self._weight,
            "weight_unit": "g",
            "calibration_approximate": config.CALIBRATION_APPROXIMATE,
            "calibration_reference_g": config.CALIBRATION_REFERENCE_G,
            "raw": self._raw,
            "hx_ok": self._hx_ok,
            "hx_error": self._hx_error,
            "weight_age_ms": (max(0, time.ticks_diff(self._now, self._weight_last_ok))
                              if self._weight_last_ok is not None else None),
            "calibrated": config.CALIBRATION_FACTOR not in (None, 0) and config.TARE_RAW is not None,
        }


def calibrar_bascula():
    """Guarda una nueva referencia solo cuando se ejecuta esta rutina manual."""
    import json
    import math
    hx = HX711(config.PIN_HX711_DOUT, config.PIN_HX711_SCK)
    print("PetCare: calibracion HX711")
    print("Deja el plato vacio montado, sin tocarlo.")
    input("Presiona Enter para medir la tara...")
    tare = hx.read_average(15, timeout_ms=200)
    print("TARE_RAW =", tare)
    known = float(input("Coloca una pesa conocida y escribe su masa en gramos (ej. 100): "))
    if not math.isfinite(known) or known <= 0:
        raise ValueError("La masa conocida debe ser mayor que cero")
    print("Esperando que la lectura se estabilice...")
    time.sleep_ms(1500)
    loaded = hx.read_average(15, timeout_ms=200)
    factor = (loaded - tare) / known
    if not math.isfinite(factor) or abs(loaded - tare) < 100:
        raise ValueError("Cambio de peso insuficiente; no se guardo calibracion")
    print("CALIBRATION_FACTOR =", factor)
    if input("Escribe GUARDAR para reemplazar la calibracion anterior: ").strip() != "GUARDAR":
        print("Se conserva la calibracion anterior.")
        return
    datos = {"TARE_RAW": tare, "CALIBRATION_FACTOR": factor,
             "masa_referencia_g": known, "referencia_aproximada": True}
    with open("calibracion_pesa_prueba.json", "w") as archivo:
        json.dump(datos, archivo)
    with open("tara_tazon.json", "w") as archivo:
        json.dump({"TARE_RAW": tare}, archivo)
    print("Guardado. Reinicia MicroPython para cargar los nuevos valores.")
