"""Prueba independiente de compuerta: GPIO33, 1350/1690 us a 50 Hz."""

from machine import Pin
from actuadores import ServoSG90
import config


def main():
    Pin(config.PIN_PUMP_RELAY, Pin.OUT, value=1 - config.PUMP_ACTIVE_LEVEL)
    Pin(config.PIN_BUZZER, Pin.OUT, value=0)
    servo = ServoSG90()
    print("\nPRUEBA SOLO SERVO - GPIO33 - 50 Hz")
    print("1 ABRIR 1350 us | 2 CERRAR 1690 us | 0 SALIR")
    print("Sin pesa, Wi-Fi, bomba ni buzzer. No hay ciclos automaticos.")
    print("Abrir y cerrar mantienen PWM; salir o Ctrl+C retira PWM.")
    try:
        while True:
            opcion = input("Opcion y Enter: ").strip()
            if opcion == "0":
                break
            if opcion not in ("1", "2"):
                print("Escribe 1, 2 o 0.")
                continue
            try:
                pulso = config.SERVO_OPEN_US if opcion == "1" else config.SERVO_CLOSED_US
                servo.move_us(pulso)
                print(("ABRIR" if opcion == "1" else "CERRAR"), pulso, "us; PWM mantenido a 50 Hz")
            except Exception as error:
                print("Error del servo:", repr(error))
    except KeyboardInterrupt:
        print("Prueba interrumpida")
    finally:
        servo.release()
        print("PWM retirado. La fuente externa sigue encendida si no la apagas.")


if __name__ == "__main__":
    main()
