# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: config.py
# Objetivo: Centralizar pines, calibración, límites y ajustes de red.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare - Equipo 08 | Sistemas Programables
# Ajustes de pines y limites. Cambia solo los valores marcados como configurables.

TEAM = ("Brandon Leonel Padilla De la Cruz", "Isaac Eliseo Flores Valencia", "Lidia Verenice Padilla Lopez")
PROJECT = "PetCare - Equipo 08"

# Entradas de sensores (ESP32 DevKit clasica)
PIN_DHT22 = 4
PIN_PIR = 27
PIN_HX711_DOUT = 19
PIN_HX711_SCK = 18
PIN_FLOAT_SWITCH = 26

# Salidas
PIN_SERVO = 33
PIN_PUMP_MOSFET = 23
PIN_BUZZER = 22       # Buzzer activo; si es pasivo, requiere PWM
PIN_LED_R = 16
PIN_LED_G = 17
PIN_LED_B = 21

# Celda de carga: deja None hasta calibrarla con el plato vacio y un peso conocido.
# El factor puede ser positivo o negativo segun como conectes A+ y A-.
CALIBRATION_FACTOR = None
TARE_RAW = None

# Contacto del flotador: GPIO26 usa pull-up interno y el contacto va a GND.
# Valor 0 significa agua disponible. Si tu flotador funciona al reves, cambia a 1.
FLOAT_WATER_PRESENT_LEVEL = 0

# Servo MG995: consignas heredadas; ajustar con la compuerta real.
# Estos valores no son grados medidos. Se mantienen pulsos de 1000 a 2000 us.
# El ensayo local 800 a 3000 us no es una calibracion ni se aplica aqui.
SERVO_CLOSED_ANGLE = 30
SERVO_OPEN_ANGLE = 75
SERVO_MIN_ANGLE = 20
SERVO_MAX_ANGLE = 90
SERVO_MIN_PULSE_US = 1000
SERVO_MAX_PULSE_US = 2000
SERVO_OPEN_TIME_MS = 900
SERVO_SETTLE_MS = 350

# Limites de seguridad
BOWL_MAX_WEIGHT_G = 250.0
PUMP_PULSE_MS = 1200
PUMP_MAX_ON_MS = 2000
SENSOR_POLL_MS = 800
DHT_POLL_MS = 2500
STATUS_PRINT_MS = 3000

# Deja vacios para ejecutar por USB sin Wi-Fi. Si los completas, el panel
# local aparece en la IP que imprime Thonny. Usa una red privada de confianza.
WIFI_SSID = ""
WIFI_PASSWORD = ""
WIFI_CONNECT_TIMEOUT_MS = 8000
WEB_PORT = 80

# MQTT opcional para comunicarse con el puente Python de la computadora.
# Escribe la IP LAN de la PC (no uses 127.0.0.1 desde el ESP32).
MQTT_HOST = ""
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASSWORD = ""
MQTT_CLIENT_ID = "petcare-equipo8-esp32"
MQTT_BASE_TOPIC = "petcare/equipo8"
MQTT_TELEMETRY_SECONDS = 10
MQTT_RETRY_SECONDS = 10
