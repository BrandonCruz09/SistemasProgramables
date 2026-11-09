# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: prueba_bomba_gpio23.py
# Objetivo: Probar SIG con un pulso limitado y apagarlo al salir.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: HX711 DT19/SCK18; DHT22 DATA4; PIR OUT27; servo33; bomba23.
# ============================================
# Primero SIN bomba. Con motor: diodo en paralelo y bomba con agua.
# V- de salida es conmutado: no puentearlo a GND.
# Prueba supervisada sin flotador; no guardar como main.py.
from machine import Pin
import time

PIN_BOMBA = 23
PULSO_MS = 800
MAXIMO_MS = 1000


def esperar(ms):
    while ms > 0:
        paso = min(ms, 20)
        time.sleep_ms(paso)
        ms -= paso


class BombaPrueba:
    def __init__(self, gpio=PIN_BOMBA):
        self.salida = Pin(gpio, Pin.OUT, value=0)

    def apagar(self):
        self.salida.value(0)

    def pulso(self, duracion_ms):
        if not 0 < duracion_ms <= MAXIMO_MS:
            raise ValueError('Duracion fuera del limite de prueba')
        try:
            self.salida.value(1)
            esperar(duracion_ms)
        finally:
            self.apagar()


def main():
    bomba = BombaPrueba()
    try:
        print('PETCARE - PRUEBA MOSFET/BOMBA GPIO23')
        print('Primera prueba: bomba DESCONECTADA; observar LED del modulo.')
        print('Con motor: diodo de proteccion instalado y bomba con agua.')
        print('No detecta nivel, flujo ni atasco. Ctrl+C interrumpe.')
        for segundo in (5, 4, 3, 2, 1):
            print('Pulso en', segundo)
            esperar(1000)
        print('SIG=1 durante 0.8 segundos')
        bomba.pulso(PULSO_MS)
        print('SIG=0. Salida apagada; comprobar fisicamente que se detuvo.')
        esperar(1000)
    except KeyboardInterrupt:
        print('Prueba cancelada.')
    finally:
        bomba.apagar()
        print('FIN: GPIO23 en 0. F5 repite; no hay bucle automatico.')


if __name__ == '__main__':
    main()
