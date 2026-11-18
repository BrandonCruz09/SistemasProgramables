# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: config.py
# Objetivo: Centralizar pines, calibración, límites y ajustes de red.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo MG995=33, bomba rele=23, buzzer=22
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
PIN_PUMP_RELAY = 23
PUMP_ACTIVE_LEVEL = 0  # HW-383 K1: LOW activa; HIGH apaga.
PUMP_TIMER_ID = 0
WATER_LEVEL_SENSOR_ENABLED = False  # Montaje actual sin flotador.
PIN_BUZZER = 22       # Buzzer activo; si es pasivo, requiere PWM

# OLED de Nebula Dash: bus dedicado en GPIO26/25.
OLED_ENABLED = True
OLED_SDA = 26
OLED_SCL = 25
OLED_ADDRESS = 0x3C
OLED_REFRESH_MS = 800

# Se cargan los archivos de calibracion al final, despues del perfil privado.
CALIBRATION_FACTOR = None
TARE_RAW = None

# Contacto del flotador: GPIO26 usa pull-up interno y el contacto va a GND.
# Valor 0 significa agua disponible. Si tu flotador funciona al reves, cambia a 1.
FLOAT_WATER_PRESENT_LEVEL = 0

# Posiciones observadas por el equipo en la compuerta instalada.
SERVO_CLOSED_US = 1690
SERVO_OPEN_US = 1350  # Ultimo ajuste solicitado; falta revalidar el conjunto alimentado.
SERVO_MIN_PULSE_US = 1350
SERVO_MAX_PULSE_US = 1690
SERVO_MOVEMENT_ENABLED = False  # Revalidar montaje tras el temblor; no rearmar automaticamente.
SERVO_MANUAL_ENABLED = True  # Apertura y cierre solicitados desde el panel.
BUZZER_ENABLED = True  # Modulo activo 3V3, señal en GPIO22.
SERVO_OPEN_TIME_MS = 900
SERVO_SETTLE_MS = 350

# Agua por tiempo; volumen real pendiente de medir.
WATER_TARGET_ML = None
PUMP_REFERENCE_FLOW_L_H = None
# Limites de seguridad
BOWL_MAX_WEIGHT_G = 300.0
FOOD_TARGET_G = 300.0
FOOD_PULSE_MS = 250
FOOD_FINE_PULSE_MS = 100
FOOD_WEIGH_WAIT_MS = 1200
FOOD_MAX_CYCLES = 30
FOOD_MAX_RUN_MS = 90000
FOOD_NO_PROGRESS_CYCLES = 3
PUMP_PULSE_MS = 5000
PUMP_MAX_ON_MS = 5000
PUMP_COOLDOWN_MS = 10000
SENSOR_POLL_MS = 800
DHT_POLL_MS = 2500
STATUS_PRINT_MS = 3000
WEIGHT_MAX_AGE_MS = 3000

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

# Ajustes privados de esta PC; este archivo no se publica en Git.
try:
    from config_local import *
except ImportError:
    pass

from calibracion_pesa import cargar
_pesa = cargar()
CALIBRATION_FACTOR = _pesa['factor']
TARE_RAW = _pesa['tara']
CALIBRATION_APPROXIMATE = _pesa['aproximada']
CALIBRATION_REFERENCE_G = _pesa['referencia_g']
CALIBRATION_ERROR = _pesa['error']
