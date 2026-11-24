# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Registrar una prueba de banco de PRUEBA SERVO AJUSTADA para PetCare.

# PetCare: prueba manual con el mismo controlador y configuracion del proyecto.
import config
from machine import Pin
from actuadores import ServoSG90

Pin(config.PIN_PUMP_RELAY, Pin.OUT, value=1-config.PUMP_ACTIVE_LEVEL)
servo = ServoSG90()
print('GPIO', config.PIN_SERVO, '| 50 Hz | abrir', config.SERVO_OPEN_US,
      'us | cerrar', config.SERVO_CLOSED_US, 'us')
print('Sin movimiento al iniciar. Sin ciclos ni alivio automatico.')
print('Con temblor o atasco: apagar la fuente. No detecta fuerza ni posicion real.')
print('Antes de repetir, separar el brazo de la tapa con la fuente apagada.')
try:
    if input('Para prueba manual supervisada escribe PROBAR: ').strip() == 'PROBAR':
        while True:
            option = input('1 Abrir y mantener | 2 Cerrar y mantener | 0 Terminar: ').strip()
            if option == '0':
                break
            if option not in ('1', '2'):
                print('Sin movimiento: usa 1, 2 o 0.')
                continue
            pulse = config.SERVO_OPEN_US if option == '1' else config.SERVO_CLOSED_US
            servo.move_us(pulse)
            print('Orden enviada:', pulse, 'us. PWM mantenido; confirma el movimiento a simple vista.')
except KeyboardInterrupt:
    print('Prueba detenida.')
except Exception as exc:
    print('Error del servo, no se repetira la orden:', repr(exc))
finally:
    servo.release()
    print('PWM retirado sin ordenar cierre. Para cortar fuerza, apaga la fuente.')
