# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Registrar una prueba de banco de PRUEBA SERVO COMPUERTA para PetCare.

# PetCare | Equipo 08 | Prueba independiente del montaje de la compuerta
# Ejecutar en Thonny con MicroPython ESP32. No requiere otros archivos.
from machine import Pin, PWM
import time

PIN_SERVO = 33
ABIERTO_US = 1340
CERRADO_US = 1690
MIN_US = 1300
MAX_US = 1850
ALIVIO_US = 1400
CIERRE_PRUEBA_MS = 3000
ESPERA_APERTURA_MS = 600  # Tiempo para observar el movimiento; NO es el pulso.


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
            raise ValueError('Usa un entero entre %s y %s us; no fuerces los topes.' % (MIN_US, MAX_US))

    def mover(self, pulso, duracion_ms):
        self.validar(pulso)
        if not 0 < duracion_ms <= CIERRE_PRUEBA_MS:
            raise ValueError('Duracion fuera del limite de esta prueba')
        if self.pwm is None:
            # Inicializar el temporizador antes de usar duty_ns (ESP32).
            duty = (pulso * 65535 + 10000) // 20000
            self.pwm = PWM(self.pin, freq=50, duty_u16=duty)
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
        except BaseException:
            self.liberar()
            raise
        print('POSICION MANTENIDA: la senal PWM sigue activa en', pasos[-1][0], 'us.')
        print('Stop o 0 retira la senal. Si zumba o se traba, apaga la fuente.')

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
        print('Ajustes temporales; vuelve a probar 1 y 2. Se mantiene la ultima posicion ordenada.')

    def menu(self):
        print('\nPETCARE - PRUEBA DE COMPUERTA - GPIO33 - 50 Hz')
        print('Primero sin croquetas. Ctrl+C o Stop retira PWM sin intentar cerrar.')
        print('No mide fuerza, atasco ni posicion real. Retirar PWM no corta los 5 V.')
        print('Abrir y cerrar CONSERVAN la senal. 600 ms es espera, no posicion.')
        try:
            while True:
                print('\nABIERTO:', self.abierto, 'us | CERRADO:', self.cerrado, 'us')
                print('1 Abrir y mantener | 2 Cerrar y mantener | 3 Ciclo normal | 4 Confirmar posiciones')
                print('5 Ajustar pulsos | 6 Alivio opcional con reapertura | 0 Salir')
                opcion = input('Opcion y Enter: ').strip()
                try:
                    if opcion == '0':
                        break
                    elif opcion == '1':
                        self.ejecutar(((self.abierto, ESPERA_APERTURA_MS),))
                    elif opcion == '2':
                        print('CERRANDO:', self.cerrado, 'us. Espera 3 segundos y conserva la senal.')
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
                    print(exc)
        except KeyboardInterrupt:
            print('\nPrueba detenida. Revisa la compuerta antes de poner croquetas.')
        finally:
            self.liberar()


if __name__ == '__main__':
    # Rele HW-383 activo LOW: mantener la bomba apagada durante esta prueba.
    Pin(23, Pin.OUT, value=1)
    # Comprobar el temporizador sin enviar pulsos al servo.
    prueba_pwm = PWM(Pin(PIN_SERVO), freq=50, duty_u16=0)
    try:
        prueba_pwm.duty_ns(0)
        time.sleep_ms(30)
        if prueba_pwm.freq() != 50 or prueba_pwm.duty_ns() != 0:
            raise RuntimeError('PWM no paso la comprobacion de inicio')
        print('PWM comprobado en ESP32: 50 Hz, sin pulsos de movimiento.')
    finally:
        prueba_pwm.deinit()
    PruebaCompuerta().menu()
