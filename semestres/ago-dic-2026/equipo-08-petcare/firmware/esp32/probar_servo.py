# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: probar_servo.py
# Objetivo: Probar el servo posicional sin compuerta y liberar PWM al terminar.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# Prueba breve del servo posicional. Ejecutar sin compuerta/palanca conectada la primera vez.
import time
import config
from actuadores import ServoSG90

servo = ServoSG90()
try:
    print("Prueba servo: centro, abrir, cerrar y liberar")
    for label, angle in (("centro", 55), ("abrir", config.SERVO_OPEN_ANGLE),
                         ("cerrar", config.SERVO_CLOSED_ANGLE)):
        print(label, angle, "grados")
        servo.move_to(angle)
        time.sleep_ms(700)
        servo.release()
        time.sleep_ms(400)
    print("Fin: si solo zumba, corta la alimentacion y revisa fuente/GND/mecanismo.")
finally:
    servo.release()
