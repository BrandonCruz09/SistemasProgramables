# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: banco_servo.py
# Objetivo: Probar el servo posicional sin carga y retirar PWM al salir.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: HX711 DT19/SCK18; DHT22 DATA4; PIR OUT27; servo33; bomba23.
# ============================================
import time
from machine import Pin, PWM


class ServoPrueba:
    PIN = 33
    FRECUENCIA = 50
    # No son extremos mecanicos; cada servo tiene su propio recorrido.
    SECUENCIA = ((1500, 'CENTRO'), (1100, 'LADO A'),
                 (1900, 'LADO B'), (1500, 'CENTRO'))

    def __init__(self):
        self.pwm = None

    def apagar(self):
        try:
            if self.pwm is not None:
                self.pwm.deinit()
        finally:
            self.pwm = None
            Pin(self.PIN, Pin.OUT, value=0)

    def ejecutar(self):
        print('PRUEBA SERVO: GPIO33, 50 Hz, sin otros sensores ni PWM.')
        print('Sin compuerta. Ctrl+C detiene y apaga la senal.')
        try:
            self.pwm = PWM(Pin(self.PIN), freq=self.FRECUENCIA, duty_u16=0)
            for pulso_us, posicion in self.SECUENCIA:
                self.pwm.duty_ns(pulso_us * 1000)
                time.sleep_ms(30)  # Esperar mas de un periodo antes de consultar PWM.
                # Esto comprueba la configuracion, no mide el cable ni el angulo.
                print(posicion, '| solicitado:', pulso_us, 'us',
                      '| PWM:', self.pwm.freq(), 'Hz',
                      '| configurado:', self.pwm.duty_ns(), 'ns')
                for _ in range(40):
                    time.sleep_ms(50)
        finally:
            self.apagar()
        print('FIN: PWM apagado. No se ha medido movimiento fisico.')

    def probar(self):
        print('MG995: senal GPIO33; rojo +5V externo; cafe/negro V-.')
        print('Unir V- con GND ESP32. Probar sin compuerta.')
        respuesta = input('Fuente lista: escribe SI y Enter. Enter solo CANCELA: ')
        if respuesta.strip().upper() != 'SI':
            print('PRUEBA CANCELADA: no se envio ningun pulso al servo.')
            return
        self.ejecutar()
