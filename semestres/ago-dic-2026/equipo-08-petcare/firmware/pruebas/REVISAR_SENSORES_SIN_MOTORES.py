# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Registrar una prueba de banco de REVISAR SENSORES SIN MOTORES para PetCare.

# PetCare: diagnostico del montaje sin dispensar comida ni agua.
import config
from machine import Pin
Pin(config.PIN_PUMP_RELAY, Pin.OUT, value=1-config.PUMP_ACTIVE_LEVEL)
Pin(config.PIN_SERVO, Pin.OUT, value=0)
config.SERVO_MOVEMENT_ENABLED = False
config.BUZZER_ENABLED = False
print('DIAGNOSTICO: sensores, OLED, panel y MQTT. Ordenes de servido bloqueadas.')
print('Factor:', config.CALIBRATION_FACTOR, '| Tara:', config.TARE_RAW)
print('No cambia calibracion ni tara. Ctrl+C o Stop para terminar.')
from main import main
main(solo_lectura=True)
