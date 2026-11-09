# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: banco_sensores.py
# Objetivo: Mostrar DHT22, PIR y báscula en pruebas separadas o conjuntas.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: HX711 DT19/SCK18; DHT22 DATA4; PIR OUT27; servo33; bomba23.
# ============================================
import time
from machine import Pin
import dht


class Sensores:
    def __init__(self):
        self.pir = Pin(27, Pin.IN, Pin.PULL_DOWN)
        self.dht = dht.DHT22(Pin(4))

    def movimiento(self, seconds=60):
        print('PIR: espera al menos 60 s desde que lo encendiste para estabilizarlo.')
        print('Prueba durante', seconds, 's. Muevete frente al sensor y luego alejate.')
        start = time.ticks_ms()
        last = None
        last_print = start
        while time.ticks_diff(time.ticks_ms(), start) < seconds * 1000:
            value = self.pir.value()
            now = time.ticks_ms()
            if value != last or time.ticks_diff(now, last_print) >= 5000:
                print('PIR:', 'MOVIMIENTO' if value else 'SIN MOVIMIENTO')
                last, last_print = value, now
            time.sleep_ms(100)

    def ambiente(self):
        self.dht.measure()
        return self.dht.temperature(), self.dht.humidity()

    def monitor(self, pesa=None, incluir_dht=True, incluir_pir=True, samples=12):
        print('Prueba limitada. Ctrl+C regresa al menu. El servo NO se mueve aqui.')
        for i in range(samples):
            parts = ['Lectura %d/%d' % (i + 1, samples)]
            if incluir_pir:
                parts.append('PIR=' + ('MOVIMIENTO' if self.pir.value() else 'SIN MOVIMIENTO'))
            if incluir_dht:
                try:
                    t, h = self.ambiente()
                    parts.append('Temperatura=%.1f C | Humedad=%.1f %%' % (t, h))
                except OSError:
                    parts.append('DHT22=SIN LECTURA; revisar DATA=4 y alimentacion')
            if pesa is not None:
                try:
                    raw, _ = pesa.muestra(5)
                    parts.append('Pesa=%.1f RAW' % raw)
                except (OSError, ValueError) as exc:
                    parts.append('Pesa=ERROR: ' + str(exc))
            print(' | '.join(parts))
            if i + 1 < samples:
                time.sleep_ms(2500)
