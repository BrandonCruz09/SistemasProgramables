# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Registrar una prueba de banco de AJUSTE SERVO PASOS CORTOS para PetCare.

# PetCare: ajuste manual de la tapa sobre su soporte de madera.
# GPIO33. El usuario confirmo 1690 us como cierre en el montaje actual.
# 1650 no es una apertura validada: es el limite de esta primera exploracion.
PIN_SERVO = 33
CERRADO_US = 1690
LIMITE_PRUEBA_US = 1650
PASO_US = 10


def siguiente_pulso(actual, paso):
    if actual is None:
        raise ValueError('Primero confirma el cierre con la opcion 1.')
    if paso not in (-PASO_US, PASO_US):
        raise ValueError('Solo se permiten pasos de 10 us.')
    nuevo = actual + paso
    if not LIMITE_PRUEBA_US <= nuevo <= CERRADO_US:
        raise ValueError('Limite de esta prueba. No se envio movimiento.')
    return nuevo


class Ajuste:
    def __init__(self):
        from machine import Pin
        self.pin = Pin(PIN_SERVO, Pin.OUT, value=0)
        self.pwm = None
        self.actual = None

    def mover(self, pulso):
        from machine import PWM
        if type(pulso) is not int or not LIMITE_PRUEBA_US <= pulso <= CERRADO_US:
            raise ValueError('Pulso fuera del intervalo de prueba.')
        if self.pwm is None:
            self.pwm = PWM(self.pin, freq=50,
                           duty_u16=(pulso*65535+10000)//20000)
        self.pwm.duty_ns(pulso*1000)
        self.actual = pulso
        print('Orden:', pulso, 'us. PWM se mantiene; observa la tapa.')
        print('Configuracion leida:', self.pwm.freq(), 'Hz;', self.pwm.duty_ns(), 'ns')

    def detener(self):
        if self.pwm is not None:
            self.pwm.deinit()
            self.pwm = None
        self.pin.value(0)
        self.actual = None


def main():
    ajuste = Ajuste()
    print('\nPETCARE - AJUSTE CORTO DE LA COMPUERTA')
    print('No se mueve al iniciar. Sin croquetas. Bomba y buzzer no se usan.')
    print('La posicion de cierre confirmada es 1690 us.')
    print('Esta prueba NO detecta el borde de la madera, fuerza ni atascos.')
    print('Cada paso requiere observar que la tapa conserva su apoyo.')
    print('Si roza, se vence o rebasa el soporte: apaga la fuente.')
    try:
        while True:
            print('\nUltima orden:', ajuste.actual, 'us (no es posicion medida)')
            print('1 Cerrar a 1690 | 2 Un paso hacia abrir (-10)')
            print('3 Un paso hacia cerrar (+10) | 4 Mostrar pulso actual | 0 Salir')
            op = input('Opcion y Enter: ').strip()
            try:
                if op == '0': break
                elif op == '1': ajuste.mover(CERRADO_US)
                elif op == '2': ajuste.mover(siguiente_pulso(ajuste.actual, -PASO_US))
                elif op == '3': ajuste.mover(siguiente_pulso(ajuste.actual, PASO_US))
                elif op == '4':
                    print('Pulso de prueba:', ajuste.actual, 'us. No se guardo en el proyecto.')
                else: print('Elige una opcion del menu.')
            except ValueError as error:
                print(error)
    finally:
        ajuste.detener()
        print('PWM retirado. Esto NO corta la alimentacion del servo.')


if __name__ == '__main__':
    main()
