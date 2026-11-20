"""OLED SSD1306, SDA26/SCL25. Su fallo no detiene el control."""

import time
import config


class PantallaPeso:
    def __init__(self):
        self.oled = None
        self.next = 0
        self.retry = 0

    def update(self, status, state, now):
        if time.ticks_diff(now, self.next) < 0:
            return
        self.next = time.ticks_add(now, 800)
        if self.oled is None:
            if time.ticks_diff(now, self.retry) < 0:
                return
            self.retry = time.ticks_add(now, 15000)
            try:
                from machine import Pin, SoftI2C
                from ssd1306 import SSD1306_I2C

                bus = SoftI2C(
                    sda=Pin(config.OLED_SDA), scl=Pin(config.OLED_SCL), freq=100000, timeout=10000
                )
                if config.OLED_ADDRESS not in bus.scan():
                    return
                self.oled = SSD1306_I2C(128, 64, bus, addr=config.OLED_ADDRESS)
            except Exception as exc:
                print("OLED:", repr(exc))
                return
        try:
            g = status.get("weight_g")
            text = "%.1f g" % g if status.get("hx_ok") and g is not None else "SIN LECTURA"
            self.oled.fill(0)
            self.oled.text("PETCARE", 0, 0)
            self.oled.text(text, 0, 20)
            self.oled.text(state[:16], 0, 40)
            self.oled.text("Tara conservada", 0, 55)
            self.oled.show()
        except Exception as exc:
            print("OLED:", repr(exc))
            self.oled = None

    def close(self):
        pass
