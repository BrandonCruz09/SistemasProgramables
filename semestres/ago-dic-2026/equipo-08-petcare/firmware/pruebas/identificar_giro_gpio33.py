# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: identificar_giro_gpio33.py
# Objetivo: Comparar dos consignas de servo sin carga en dos ciclos finitos.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: HX711 DT19/SCK18; DHT22 DATA4; PIR OUT27; servo33; bomba23.
# ============================================
# Sin carga. No usar 9 V. No guardar como main.py.
# 1000/2000 us no garantizan 0/180 grados.
from machine import Pin, PWM
import time

PIN_SERVO = 33
FRECUENCIA_HZ = 50
EXTREMO_A_US = 1000
CENTRO_US = 1500
EXTREMO_B_US = 2000
PAUSA_MS = 2000
CICLOS = 2


def esperar(ms):
    # Pausas cortas permiten interrumpir con Ctrl+C.
    while ms > 0:
        paso = min(ms, 20)
        time.sleep_ms(paso)
        ms -= paso


def escribir_pulso(pwm, pulso_us):
    if not EXTREMO_A_US <= pulso_us <= EXTREMO_B_US:
        raise ValueError('Pulso fuera del rango de prueba')
    pwm.duty_u16(pulso_us * 65535 // 20000)


def mover_suave(pwm, actual, destino):
    # El valor actual es la ultima orden; no es una posicion medida.
    paso = 10 if destino > actual else -10
    while actual != destino:
        if abs(destino - actual) <= 10:
            actual = destino
        else:
            actual += paso
        escribir_pulso(pwm, actual)
        esperar(20)
    return actual


def main():
    pwm = None
    print('PRUEBA V2: AMBOS EXTREMOS - GPIO33 - 50 Hz')
    print('Sin compuerta, sin paletas y sin croquetas.')
    print('Centro -> A (1000 us) -> B (2000 us); dos ciclos.')
    print('La derecha/izquierda depende de como este montado el servo.')
    print('Si zumba contra un tope: Ctrl+C y apagar su fuente.')
    try:
        for segundo in (3, 2, 1):
            print('Inicio en', segundo)
            esperar(1000)
        pwm = PWM(Pin(PIN_SERVO), freq=FRECUENCIA_HZ, duty_u16=0)
        actual = CENTRO_US
        escribir_pulso(pwm, actual)
        print('CENTRO - orden 1500 us')
        esperar(PAUSA_MS)
        for ciclo in range(1, CICLOS + 1):
            for nombre, destino in (('A', EXTREMO_A_US), ('B', EXTREMO_B_US)):
                print('Ciclo', ciclo, '- moviendo al EXTREMO', nombre, '-', destino, 'us')
                actual = mover_suave(pwm, actual, destino)
                print('Orden mantenida 2 s. Observar el movimiento real.')
                esperar(PAUSA_MS)
        print('Regreso al CENTRO')
        mover_suave(pwm, actual, CENTRO_US)
        esperar(1000)
    except KeyboardInterrupt:
        print('Interrumpido por el usuario.')
    finally:
        try:
            if pwm is not None:
                pwm.deinit()
        finally:
            Pin(PIN_SERVO, Pin.OUT, value=0)
        print('PWM APAGADO. Prueba terminada; no se repite sola.')
        print('Si sigue girando, apagar su fuente.')
    print('Comparar A contra B: amplio, pequeno o sin movimiento.')


if __name__ == '__main__':
    main()
