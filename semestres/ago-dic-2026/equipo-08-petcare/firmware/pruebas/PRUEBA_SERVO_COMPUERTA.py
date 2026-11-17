# PetCare | Equipo 08 | Prueba independiente del montaje de la compuerta
# Ejecutar en Thonny con MicroPython ESP32. No requiere otros archivos.
from machine import Pin, PWM
import time

PIN_SERVO = 33
ABIERTO_US = 1600
CERRADO_US = 1850
MIN_US = 1500
MAX_US = 1850
ALIVIO_US = 150
CIERRE_PRUEBA_MS = 3000


def secuencia_cierre(abierto, cerrado):
    # Una sola reapertura corta; no detecta un atasco ni verifica el cierre.
    sentido = 1 if abierto > cerrado else -1
    alivio = cerrado + sentido * min(ALIVIO_US, abs(cerrado - abierto) // 3)
    return ((cerrado, 350), (alivio, 250), (cerrado, 500))


class PruebaCompuerta:
    def __init__(self):
        self.pin = Pin(PIN_SERVO, Pin.OUT, value=0)
        self.pwm = None
        self.abierto = ABIERTO_US
        self.cerrado = CERRADO_US
        self.ajustes_confirmados = False

    def liberar(self):
        try:
            if self.pwm is not None:
                self.pwm.deinit()
        finally:
            self.pwm = None
            self.pin.value(0)

    @staticmethod
    def validar(pulso):
        if type(pulso) is not int or not MIN_US <= pulso <= MAX_US:
            raise ValueError('Usa un entero entre 1500 y 1850 us; no fuerces los topes.')

    def mover(self, pulso, duracion_ms):
        self.validar(pulso)
        if not 0 < duracion_ms <= CIERRE_PRUEBA_MS:
            raise ValueError('Duracion fuera del limite de esta prueba')
        if self.pwm is None:
            self.pwm = PWM(self.pin, freq=50, duty_u16=0)
        print('Orden:', pulso, 'us durante', duracion_ms, 'ms')
        self.pwm.duty_ns(pulso * 1000)
        # Esperas breves para responder a Ctrl+C durante la prueba.
        inicio = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), inicio) < duracion_ms:
            time.sleep_ms(20)

    def ejecutar(self, pasos):
        try:
            for pulso, duracion in pasos:
                self.mover(pulso, duracion)
        finally:
            self.liberar()
        print('AHORA SE RETIRO PWM. No se envio ninguna orden de abrir.')
        print('Si la tapa regresa justo ahora, anotalo: falta comprobar su soporte mecanico.')

    def ciclo(self, con_alivio=False):
        if not self.ajustes_confirmados:
            print('Primero prueba 1 y 2 sin croquetas y confirma las posiciones con 4.')
            return
        cierre = (secuencia_cierre(self.abierto, self.cerrado) if con_alivio
                  else ((self.cerrado, CIERRE_PRUEBA_MS),))
        self.ejecutar(((self.abierto, 900),) + cierre)
        if con_alivio:
            print('Alivio solicitado: una reapertura corta y un segundo cierre.')
            print('Si sigue atorado: apaga la fuente y retira la croqueta; no repitas.')
        else:
            print('Ciclo normal terminado: abrir y cerrar, sin reapertura programada.')

    def ajustar(self):
        # Ajustes temporales: no sobrescriben la configuracion del proyecto.
        nuevo_a = int(input('Pulso ABIERTO en us (actual %s): ' % self.abierto))
        nuevo_c = int(input('Pulso CERRADO en us (actual %s): ' % self.cerrado))
        self.validar(nuevo_a)
        self.validar(nuevo_c)
        if abs(nuevo_a - nuevo_c) < 100:
            raise ValueError('Deja al menos 100 us entre las dos posiciones.')
        self.abierto, self.cerrado = nuevo_a, nuevo_c
        self.ajustes_confirmados = False
        print('Ajustes temporales; vuelve a probar 1 y 2. No se movio el servo.')

    def menu(self):
        print('\nPETCARE - PRUEBA DE COMPUERTA - GPIO33 - 50 Hz')
        print('Primero sin croquetas. Ctrl+C o Stop retira PWM sin intentar cerrar.')
        print('No mide fuerza, atasco ni posicion real. Retirar PWM no corta los 5 V.')
        try:
            while True:
                print('\nABIERTO:', self.abierto, 'us | CERRADO:', self.cerrado, 'us')
                print('1 Abrir | 2 Cerrar 3 segundos | 3 Ciclo normal | 4 Confirmar posiciones')
                print('5 Ajustar pulsos | 6 Alivio opcional con reapertura | 0 Salir')
                opcion = input('Opcion y Enter: ').strip()
                try:
                    if opcion == '0':
                        break
                    elif opcion == '1':
                        self.ejecutar(((self.abierto, 600),))
                    elif opcion == '2':
                        print('CERRANDO:', self.cerrado, 'us durante 3 segundos; observa si se regresa.')
                        self.ejecutar(((self.cerrado, CIERRE_PRUEBA_MS),))
                    elif opcion == '3':
                        self.ciclo()
                    elif opcion == '4':
                        respuesta = input('Ya probe 1 y 2: no roza, no zumba y cierra. Escribe SI: ')
                        self.ajustes_confirmados = respuesta.strip().upper() == 'SI'
                    elif opcion == '5':
                        self.ajustar()
                    elif opcion == '6':
                        self.ciclo(con_alivio=True)
                    else:
                        print('Escribe una opcion del 0 al 6; Enter solo no mueve nada.')
                except ValueError as exc:
                    self.liberar()
                    print(exc)
        except KeyboardInterrupt:
            print('\nPrueba detenida. Revisa la compuerta antes de poner croquetas.')
        finally:
            self.liberar()


if __name__ == '__main__':
    # Rele HW-383 activo LOW: mantener la bomba apagada durante esta prueba.
    Pin(23, Pin.OUT, value=1)
    PruebaCompuerta().menu()
