# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: probar_servo.py
# Objetivo: Probar el servo posicional sin compuerta y liberar PWM al terminar.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo MG995=33, bomba rele=23, buzzer=22, RGB=16/17/21
# ============================================
# Prueba breve del servo posicional. Ejecutar sin compuerta/palanca conectada la primera vez.
import time
import config
from actuadores import ServoSG90

servo = ServoSG90()
try:
    print("Ciclo de compuerta GPIO33: cerrado 1850 us, abierto 800 us")
    input("Deja libre el mecanismo. Enter inicia; Ctrl+C cancela: ")
    for label, pulse in (("cerrar", config.SERVO_CLOSED_US),
                         ("abrir", config.SERVO_OPEN_US),
                         ("cerrar", config.SERVO_CLOSED_US)):
        print(label, pulse, "us")
        servo.move_us(pulse)
        time.sleep_ms(1000)
    print("Fin del ciclo. Verifica el movimiento fisicamente.")
finally:
    servo.release()
