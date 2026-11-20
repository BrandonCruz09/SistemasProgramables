"""HX711 canal A, ganancia 128. Lectura sin esperar conversiones en el bucle."""

import time
from machine import Pin, disable_irq, enable_irq


class HX711:
    def __init__(self, dout_pin, sck_pin):
        self.dout = Pin(dout_pin, Pin.IN)
        self.sck = Pin(sck_pin, Pin.OUT, value=0)
        # Reiniciar el protocolo, no la calibracion. Asegura canal A/128.
        self.sck.value(1)
        time.sleep_us(80)
        self.sck.value(0)
        self.settle_until = time.ticks_add(time.ticks_ms(), 450)

    def ready(self):
        return time.ticks_diff(time.ticks_ms(), self.settle_until) >= 0 and self.dout.value() == 0

    def read_ready(self):
        if not self.ready():
            return None
        value = 0
        irq = disable_irq()
        try:
            for _ in range(24):
                self.sck.value(1)
                time.sleep_us(1)
                value = (value << 1) | self.dout.value()
                self.sck.value(0)
                time.sleep_us(1)
            self.sck.value(1)
            time.sleep_us(1)
            self.sck.value(0)  # Pulso 25: canal A, 128; no cambiar canal al reiniciar.
        finally:
            self.sck.value(0)
            enable_irq(irq)
        if value & 0x800000:
            value -= 0x1000000
        if abs(value) >= 8388000:
            raise ValueError("HX711 saturado")
        return value

    def read_raw(self, timeout_ms=500):
        inicio = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), inicio) < timeout_ms:
            value = self.read_ready()
            if value is not None:
                return value
            time.sleep_ms(1)
        raise OSError("HX711 sin dato")

    def read_average(self, samples=5, timeout_ms=500):
        if samples < 1:
            raise ValueError("Cantidad de muestras invalida")
        return sum(self.read_raw(timeout_ms) for _ in range(samples)) / samples
