# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: probar_salidas.py
# Objetivo: Probar salidas individualmente con supervisión física.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# Prueba de RGB, buzzer activo y bomba por un pulso corto.
# Ejecuta con la bomba desconectada primero; revisa el MOSFET antes de conectar agua.
import time
from actuadores import PumpMOSFET, ActiveBuzzer, RGBLed

led = RGBLed()
buzzer = ActiveBuzzer()
pump = PumpMOSFET()
try:
    for color in ("red", "green", "blue", "yellow", "off"):
        print("LED:", color)
        led.set_color(color)
        time.sleep_ms(500)
    print("Buzzer activo 100 ms")
    buzzer.on(); time.sleep_ms(100); buzzer.off()
    print("Pulso de MOSFET 300 ms; solo si ya verificaste el circuito")
    pump.on(); time.sleep_ms(300); pump.off()
finally:
    pump.off(); buzzer.off(); led.set_color("off")
print("Prueba terminada")
