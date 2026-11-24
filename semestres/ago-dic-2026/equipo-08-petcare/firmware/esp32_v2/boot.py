# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Arrancar el microcontrolador sin activar cargas al inicio.

# Salidas inactivas antes de importar el programa.
from machine import Pin

Pin(23, Pin.OUT, value=1)
Pin(22, Pin.OUT, value=0)
Pin(33, Pin.OUT, value=0)
