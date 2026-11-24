# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Mostrar peso y estado de la báscula en una pantalla OLED.

# Sistemas Programables | PetCare | Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez.
# OLED SSD1306 128x64: SDA26, SCL25, VCC3V3 y GND.
import math
import time
import config


def texto_peso(status):
    if not status.get('calibrated'):
        return 'SIN CALIBRAR'
    value = status.get('weight_g')
    if (not status.get('hx_ok') or isinstance(value, bool)
            or not isinstance(value, (int, float)) or not math.isfinite(value)):
        return 'SIN LECTURA'
    return '%.1f g' % value


class PantallaPeso:
    def __init__(self):
        self.oled = None
        self.last_update = None
        if not config.OLED_ENABLED:
            return
        try:
            from machine import Pin, SoftI2C
            from ssd1306 import SSD1306_I2C
            bus = SoftI2C(sda=Pin(config.OLED_SDA), scl=Pin(config.OLED_SCL),
                          freq=100000, timeout=10000)
            if config.OLED_ADDRESS not in bus.scan():
                raise OSError('No responde OLED 0x3C')
            self.oled = SSD1306_I2C(128, 64, bus, addr=config.OLED_ADDRESS)
        except Exception as error:
            print('OLED no disponible; el resto sigue funcionando:', error)

    def update(self, status, state, now_ms):
        if self.oled is None:
            return
        if self.last_update is not None and time.ticks_diff(now_ms, self.last_update) < config.OLED_REFRESH_MS:
            return
        self.last_update = now_ms
        try:
            display = self.oled
            display.fill(0)
            display.text('PETCARE PESO', 0, 0)
            text = texto_peso(status)
            if len(text) <= 8:
                import framebuf
                small = framebuf.FrameBuffer(bytearray(64), 64, 8, framebuf.MONO_HLSB)
                small.text(text, 0, 0)
                for y in range(8):
                    for x in range(len(text)*8):
                        if small.pixel(x, y):
                            display.fill_rect(x*2, 17+y*2, 2, 2, 1)
            else:
                display.text(text[:16], 0, 20)
            label = 'LECTURA EN PAUSA' if status.get('readings_paused') or state == 'BOMBA_ACTIVA' else state
            display.text(label[:16], 0, 42)
            display.text('Ref. aproximada' if status.get('calibration_approximate') else 'Peso neto', 0, 55)
            display.show()
        except Exception as error:
            print('OLED desconectada; lectura sigue por consola:', error)
            self.oled = None

    def close(self):
        if self.oled is not None:
            try:
                self.oled.fill(0)
                self.oled.text('DETENIDO', 0, 25)
                self.oled.show()
            except Exception:
                pass
