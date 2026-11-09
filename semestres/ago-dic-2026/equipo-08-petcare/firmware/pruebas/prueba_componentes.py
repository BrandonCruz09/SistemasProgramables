# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: prueba_componentes.py
# Objetivo: Seleccionar pruebas manuales sin activar actuadores al iniciar.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: HX711 DT19/SCK18; DHT22 DATA4; PIR OUT27; servo33; bomba23.
# ============================================
from banco_pesa import Pesa
from banco_sensores import Sensores
from banco_servo import ServoPrueba


def main():
    pesa = Pesa()
    sensores = Sensores()
    servo = ServoPrueba()
    try:
        while True:
            print('\nPETCARE - PRUEBA DE COMPONENTES')
            print('Pesa: lectura directa RAW (unidades del sensor, no gramos)')
            print('1 Leer pesa directamente')
            print('3 Probar DHT22 (temperatura y humedad)')
            print('4 Probar PIR (movimiento)')
            print('5 Probar MG995 (solo esta opcion mueve el servo)')
            print('6 Ver pesa + DHT22 + PIR juntos')
            print('0 Salir y apagar PWM')
            try:
                opcion = input('Elige un numero y presiona Enter: ').strip()
                if opcion == '0':
                    break
                elif opcion in ('1', '2'):
                    sensores.monitor(pesa, False, False)
                elif opcion == '3':
                    sensores.monitor(None, True, False)
                elif opcion == '4':
                    sensores.movimiento()
                elif opcion == '5':
                    servo.probar()
                elif opcion == '6':
                    sensores.monitor(pesa)
                else:
                    print('Opcion no valida.')
            except KeyboardInterrupt:
                servo.apagar()
                print('Prueba interrumpida. Usa 0 para salir del programa.')
            except (OSError, ValueError, TypeError) as exc:
                servo.apagar()
                print('No se completo la prueba:', exc)
    finally:
        servo.apagar()
        print('Programa terminado. F5 vuelve a abrir el menu.')


if __name__ == '__main__':
    main()
