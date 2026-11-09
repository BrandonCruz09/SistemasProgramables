# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: hx711.py
# Objetivo: Leer la celda con límite de espera y muestreo del HX711.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: HX711 DT19/SCK18; DHT22 DATA4; PIR OUT27; servo33; bomba23.
# ============================================
import time


class HX711:
    def __init__(self, dout_pin, sck_pin):
        from machine import Pin
        self.dout = Pin(dout_pin, Pin.IN)
        self.sck = Pin(sck_pin, Pin.OUT, value=0)

    @staticmethod
    def _ticks_diff(a, b):
        try:
            return time.ticks_diff(a, b)
        except AttributeError:
            return a - b

    def read_raw(self, timeout_ms=80):
        """Lee 24 bits con ganancia 128; termina con timeout si el modulo no responde."""
        start = time.ticks_ms()
        while self.dout.value():
            if self._ticks_diff(time.ticks_ms(), start) >= timeout_ms:
                raise OSError("HX711 sin dato: revisa VCC, GND, DT y SCK")
            time.sleep_ms(1)

        value = 0
        for _ in range(24):
            self.sck.value(1)
            value = (value << 1) | self.dout.value()
            self.sck.value(0)

        # Pulso 25: siguiente conversion con ganancia 128, canal A.
        self.sck.value(1)
        self.sck.value(0)

        if value & 0x800000:
            value -= 0x1000000
        return value

    def read_average(self, samples=3, timeout_ms=80):
        if samples < 1:
            raise ValueError("samples debe ser al menos 1")
        total = 0
        count = 0
        for _ in range(samples):
            total += self.read_raw(timeout_ms)
            count += 1
        return total / count
