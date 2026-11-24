"""Prueba individual supervisada. No modifica calibracion ni inicia ciclos solos."""
# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Documentar el uso de prueba manual dentro del proyecto PetCare.

import time
import config
from actuadores import ServoMG995, PumpRelay, ActiveBuzzer
from sensores import SensorHub


def main():
    servo = ServoMG995()
    pump = PumpRelay()
    buzzer = ActiveBuzzer()
    sensores = SensorHub()
    print("Prueba individual. Servo 850/1500 us. Agua maximo 5 s.")
    print("Para agua: bomba sumergida y espacio en el tazon. Sin croquetas para servo.")
    try:
        while True:
            choice = input(
                "1 abrir | 2 cerrar | 3 agua 5 s | 4 buzzer activo | 5 tono pasivo | 6 sensores | 0 salir: "
            ).strip()
            try:
                if choice == "0":
                    break
                if choice in ("1", "2"):
                    servo.move_us(config.SERVO_OPEN_US if choice == "1" else config.SERVO_CLOSED_US)
                    print("PWM mantenido:", servo.pulse, "us a", servo.pwm.freq(), "Hz")
                elif choice == "3":
                    if input("Escribe AGUA si esta sumergida y hay espacio: ").strip() != "AGUA":
                        continue
                    pump.on(5000)
                    while pump.active:
                        pump.tick(time.ticks_ms())
                        time.sleep_ms(10)
                    print("GPIO23 inactivo; verifica fisicamente el flujo")
                elif choice in ("4", "5"):
                    buzzer.on(1500, "active" if choice == "4" else "passive")
                    servo.verify()
                    while buzzer.until is not None:
                        buzzer.tick(time.ticks_ms())
                        time.sleep_ms(10)
                    print("Senal terminada; confirma si hubo sonido")
                elif choice == "6":
                    for _ in range(600):
                        status = sensores.read(time.ticks_ms())
                        if _ % 100 == 0:
                            print(status)
                        time.sleep_ms(10)
            except Exception as exc:
                pump.off()
                buzzer.off()
                print("Error:", repr(exc))
    except KeyboardInterrupt:
        pass
    finally:
        pump.off()
        buzzer.off()
        servo.release()
        print("Salidas apagadas")


if __name__ == "__main__":
    main()
