# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).

# Sistemas Programables - PetCare, Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez. Objetivo: apagar K1 al arrancar MicroPython.
# Pin GPIO23 -> IN1 del rele HW-383, activo en LOW.
from machine import Pin
Pin(23, Pin.OUT, value=1)
