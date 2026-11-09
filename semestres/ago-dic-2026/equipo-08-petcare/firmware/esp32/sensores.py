# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: sensores.py
# Objetivo: Leer sensores y filtrar el peso con promedio y suavizado exponencial.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare - lectura y filtrado ligero de sensores.
import time
import config
from hx711 import HX711


class SensorHub:
    def __init__(self):
        from machine import Pin
        import dht
        self._dht = dht.DHT22(Pin(config.PIN_DHT22))
        self._pir = Pin(config.PIN_PIR, Pin.IN, Pin.PULL_DOWN)
        self._float = Pin(config.PIN_FLOAT_SWITCH, Pin.IN, Pin.PULL_UP)
        self._hx = HX711(config.PIN_HX711_DOUT, config.PIN_HX711_SCK)
        self._last_poll = None
        self._last_dht = None
        self._temperature = None
        self._humidity = None
        self._dht_ok = False
        self._weight = None
        self._hx_ok = False
        self._raw = None

    def read(self, now_ms=None):
        if now_ms is None:
            now_ms = time.ticks_ms()
        if self._last_poll is not None and time.ticks_diff(now_ms, self._last_poll) < config.SENSOR_POLL_MS:
            return self._snapshot()
        self._last_poll = now_ms

        if self._last_dht is None or time.ticks_diff(now_ms, self._last_dht) >= config.DHT_POLL_MS:
            self._last_dht = now_ms
            try:
                self._dht.measure()
                self._temperature = self._dht.temperature()
                self._humidity = self._dht.humidity()
                self._dht_ok = True
            except Exception:
                self._dht_ok = False

        try:
            self._raw = self._hx.read_average(3, timeout_ms=40)
            self._hx_ok = True
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
        except Exception:
            self._hx_ok = False
            self._weight = None

        return self._snapshot()

    def _snapshot(self):
        water_level = self._float.value()
        return {
            "pir": bool(self._pir.value()),
            "water_available": water_level == config.FLOAT_WATER_PRESENT_LEVEL,
            "temperature_c": self._temperature,
            "humidity_pct": self._humidity,
            "dht_ok": self._dht_ok,
            "weight_g": self._weight,
            "raw": self._raw,
            "hx_ok": self._hx_ok,
            "calibrated": config.CALIBRATION_FACTOR not in (None, 0) and config.TARE_RAW is not None,
        }


def calibrar_bascula():
    """Imprime las lecturas para obtener TARE_RAW y CALIBRATION_FACTOR."""
    from machine import Pin
    hx = HX711(config.PIN_HX711_DOUT, config.PIN_HX711_SCK)
    print("PetCare: calibracion HX711")
    print("Deja el plato vacio montado, sin tocarlo.")
    input("Presiona Enter para medir la tara...")
    tare = hx.read_average(15, timeout_ms=200)
    print("TARE_RAW =", tare)
    known = float(input("Coloca una pesa conocida y escribe su masa en gramos (ej. 100): "))
    if known <= 0:
        raise ValueError("La masa conocida debe ser mayor que cero")
    print("Esperando que la lectura se estabilice...")
    time.sleep_ms(1500)
    loaded = hx.read_average(15, timeout_ms=200)
    factor = (loaded - tare) / known
    print("CALIBRATION_FACTOR =", factor)
    print("Copia ambos valores a config.py y vuelve a ejecutar main.py.")
