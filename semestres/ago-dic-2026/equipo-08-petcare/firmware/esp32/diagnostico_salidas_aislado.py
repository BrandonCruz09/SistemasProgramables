"""Prueba manual sin Wi-Fi, MQTT, sensores ni cambios de calibracion.

Primero: bomba separada de NO/K1. No modifica main.py ni arranca un ciclo.
Servo GPIO33: abrir 850 us, cerrar 1500 us. Rele IN1 GPIO23, activo LOW.
Buzzer S GPIO22. La opcion de tono sirve para distinguir un modulo pasivo.
Salir retira PWM: la compuerta puede perder la fuerza que la sostiene.
"""
# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Documentar el uso de diagnostico salidas aislado dentro del proyecto PetCare.

from machine import Pin, PWM
from time import sleep_ms, sleep_us, ticks_ms, ticks_diff


def probar_rele(pin):
    print('GPIO23 LOW durante 3 s. Escucha el clic; el LED no basta.')
    try:
        pin.value(0)
        sleep_ms(3000)
    finally:
        pin.value(1)
        print('GPIO23 HIGH: rele apagado. Debe escucharse otro clic.')


def probar_buzzer(pin, tono=False):
    print('GPIO22: tono alterno de prueba' if tono else 'GPIO22: nivel HIGH 2 s')
    try:
        if tono:
            inicio = ticks_ms()
            while ticks_diff(ticks_ms(), inicio) < 2000:
                pin.value(1)
                sleep_us(250)
                pin.value(0)
                sleep_us(250)
        else:
            pin.value(1)
            sleep_ms(2000)
    finally:
        pin.value(0)
    print('Buzzer apagado. Confirma si se escucho un sonido continuo.')


def main():
    rele = Pin(23, Pin.OUT, value=1)
    buzzer = Pin(22, Pin.OUT, value=0)
    servo_pin = Pin(33, Pin.OUT, value=0)
    servo = None
    print('PRUEBA AISLADA. Ningun movimiento automatico.')
    print('Primero desconecta la bomba de NO/K1 con la fuente apagada.')
    print('No se mide voltaje, movimiento ni continuidad desde el programa.')
    try:
        while True:
            print('\n1 Rele 3 s | 2 Cerrar 1500 us | 3 Abrir 850 us')
            print('4 Buzzer nivel 2 s | 5 Buzzer tono 2 s | 0 Salir')
            opcion = input('Opcion y Enter: ').strip()
            try:
                if opcion == '0':
                    break
                if opcion == '1':
                    probar_rele(rele)
                elif opcion in ('2', '3'):
                    pulso = 1500 if opcion == '2' else 850
                    if servo is None:
                        servo = PWM(servo_pin, freq=50, duty_ns=pulso * 1000)
                    else:
                        servo.duty_ns(pulso * 1000)
                    print('PWM configurado:', servo.freq(), 'Hz;', servo.duty_ns(),
                          'ns. Se mantiene hasta otra orden o salida.')
                elif opcion in ('4', '5'):
                    probar_buzzer(buzzer, tono=opcion == '5')
                else:
                    print('Elige una opcion de 0 a 5.')
            except Exception as exc:
                rele.value(1)
                buzzer.value(0)
                print('ERROR:', repr(exc), 'No se repite la orden.')
    except (KeyboardInterrupt, EOFError):
        print('\nPrueba detenida.')
    finally:
        rele.value(1)
        buzzer.value(0)
        if servo is not None:
            servo.deinit()
        servo_pin.value(0)
        print('Rele y buzzer apagados. PWM retirado; servo sin sujecion electrica.')


if __name__ == '__main__':
    main()
