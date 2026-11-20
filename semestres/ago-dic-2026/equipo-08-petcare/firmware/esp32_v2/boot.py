# Salidas inactivas antes de importar el programa.
from machine import Pin

Pin(23, Pin.OUT, value=1)
Pin(22, Pin.OUT, value=0)
Pin(33, Pin.OUT, value=0)
