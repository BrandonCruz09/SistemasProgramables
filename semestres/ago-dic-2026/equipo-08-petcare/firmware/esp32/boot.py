# Sistemas Programables - PetCare, Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez. Objetivo: apagar K1 al arrancar MicroPython.
# Pin GPIO23 -> IN1 del rele HW-383, activo en LOW.
from machine import Pin
Pin(23, Pin.OUT, value=1)
