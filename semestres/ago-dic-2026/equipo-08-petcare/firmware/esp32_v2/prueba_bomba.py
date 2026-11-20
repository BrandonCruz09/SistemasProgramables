"""Prueba independiente del rele y bomba en GPIO23, activo LOW."""

import time
from machine import Pin
from actuadores import PumpRelay
import config


def main():
    Pin(config.PIN_SERVO, Pin.OUT, value=0)
    Pin(config.PIN_BUZZER, Pin.OUT, value=0)
    bomba = PumpRelay()
    print("\nPRUEBA SOLO BOMBA - RELE IN1 EN GPIO23")
    print("Servo sin PWM y buzzer apagado. Sin Wi-Fi ni pesa.")
    print("Antes de 1: bomba sumergida, manguera al tazon y espacio para el agua.")
    print("1 ENCENDER 5 SEGUNDOS | 2 APAGAR | 0 SALIR")
    print("Durante el pulso, Ctrl+C apaga inmediatamente la salida.")
    try:
        while True:
            opcion = input("Opcion y Enter: ").strip()
            if opcion == "0":
                break
            try:
                if opcion == "1":
                    bomba.on(5000)
                    inicio = time.ticks_ms()
                    ultimo = -1
                    while bomba.active:
                        now = time.ticks_ms()
                        bomba.tick(now)
                        segundo = time.ticks_diff(now, inicio) // 1000
                        if segundo != ultimo and bomba.active:
                            ultimo = segundo
                            print("Orden ON: GPIO23=0 |", 5 - segundo, "s restantes")
                        time.sleep_ms(10)
                    bomba.off()
                    print("Orden OFF: GPIO23=1. Verifica clic y flujo fisicamente.")
                elif opcion == "2":
                    bomba.off()
                    print("Salida apagada: GPIO23=1")
                else:
                    print("Escribe 1, 2 o 0.")
            except Exception as error:
                bomba.off()
                print("Error, salida apagada:", repr(error))
    except KeyboardInterrupt:
        print("Prueba interrumpida")
    finally:
        bomba.off()
        print("Rele desactivado por software")


if __name__ == "__main__":
    main()
