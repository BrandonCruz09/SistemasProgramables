"""PetCare: GPIO del montaje y limites acordados. Sin RGB ni flotador."""

VERSION = "petcare-19nov-r4"
PIN_DHT22 = 4
PIN_PIR = 27
PIN_HX711_DOUT = 19
PIN_HX711_SCK = 18
PIN_SERVO = 33
PIN_PUMP_RELAY = 23
PIN_BUZZER = 22
OLED_SDA = 26
OLED_SCL = 25
OLED_ADDRESS = 0x3C
SERVO_OPEN_US = 1350
SERVO_CLOSED_US = 1690
PUMP_ACTIVE_LEVEL = 0
PUMP_PULSE_MS = 5000
FOOD_TARGET_G = 300.0
FOOD_MAX_RUN_MS = 90000
FOOD_PULSE_MS = 250
FOOD_FINE_PULSE_MS = 100
FOOD_WEIGH_WAIT_MS = 1200
AUTO_SERVE_ENABLED = True
FOOD_EMPTY_G = 20.0
AUTO_FOOD_COOLDOWN_MS = 4 * 3600 * 1000
AUTO_WATER_COOLDOWN_MS = 2 * 3600 * 1000
AUTO_WATER_PENDING_MS = 120000
SERVO_CLOSE_ON_START = True
WEIGHT_MAX_AGE_MS = 1500
BUZZER_MODE = "passive"
BUZZER_ACTIVE_LEVEL = 1
BUZZER_FREQUENCY = 2000
OLED_ENABLED = True
BUZZER_ENABLED = True
SERVO_MOVEMENT_ENABLED = True
SERVO_MANUAL_ENABLED = True
WATER_LEVEL_SENSOR_ENABLED = False
WIFI_SSID = ""
WIFI_PASSWORD = ""
MQTT_HOST = ""
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASSWORD = ""
MQTT_CLIENT_ID = "petcare-equipo8-esp32"
MQTT_BASE_TOPIC = "petcare/equipo8"
WEB_PORT = 80

# La configuracion privada solo puede modificar red, nunca GPIO o calibracion.
try:
    import config_local as privado

    for nombre in (
        "WIFI_SSID",
        "WIFI_PASSWORD",
        "MQTT_HOST",
        "MQTT_PORT",
        "MQTT_USER",
        "MQTT_PASSWORD",
        "MQTT_CLIENT_ID",
        "MQTT_BASE_TOPIC",
    ):
        if hasattr(privado, nombre):
            globals()[nombre] = getattr(privado, nombre)
except ImportError:
    pass


def comprobar_pines():
    pines = (
        PIN_DHT22,
        PIN_PIR,
        PIN_HX711_DOUT,
        PIN_HX711_SCK,
        PIN_SERVO,
        PIN_PUMP_RELAY,
        PIN_BUZZER,
        OLED_SDA,
        OLED_SCL,
    )
    if len(set(pines)) != len(pines):
        raise ValueError("GPIO repetido en config.py")
    if not 500 <= SERVO_OPEN_US <= 2500 or not 500 <= SERVO_CLOSED_US <= 2500:
        raise ValueError("Pulso del servo fuera de rango")


comprobar_pines()
