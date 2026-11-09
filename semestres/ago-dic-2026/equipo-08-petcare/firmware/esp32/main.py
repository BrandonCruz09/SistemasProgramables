# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: main.py
# Objetivo: Inicializar módulos y ejecutar el ciclo de supervisión con apagado al detener.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare | Equipo 08 | Sistemas Programables
# Objetivo: supervisar sensores y accionar una compuerta con servo posicional y una bomba con MOSFET.
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo=33,
# MOSFET bomba=23, buzzer=22, LED RGB=16/17/21. Ver CONEXIONES_PROTOTIPO.txt.

import time
import config
from sensores import SensorHub
from actuadores import ServoSG90, PumpMOSFET, ActiveBuzzer, RGBLed
from controlador import PetCareController
from wifi_panel import connect_wifi, WebDashboard
from mqtt_link import MQTTLink


def main():
    print("\nPetCare | Equipo 08")
    for name in config.TEAM:
        print(" - " + name)
    print("Iniciando en modo seguro: bomba apagada y servo sin PWM.")

    sensors = SensorHub()
    servo = ServoSG90()
    pump = PumpMOSFET()
    buzzer = ActiveBuzzer()
    led = RGBLed()
    controller = PetCareController(sensors, servo, pump, buzzer, led)
    dashboard = None
    mqtt_link = MQTTLink()

    _wlan, _ip = connect_wifi()
    if _ip:
        try:
            dashboard = WebDashboard()
            dashboard.start()
        except Exception as exc:
            print("Panel web no disponible:", exc)
            dashboard = None

    print("Listo. Detener en Thonny con el boton Stop; el ciclo no tiene esperas largas.")
    if config.CALIBRATION_FACTOR in (None, 0) or config.TARE_RAW is None:
        print("Pendiente: calibrar HX711 antes de permitir servir alimento.")

    last_print = time.ticks_ms()
    try:
        while True:
            now = time.ticks_ms()
            status = controller.tick(now)
            if dashboard:
                dashboard.poll(controller)
            mqtt_link.poll(now, controller)
            if time.ticks_diff(now, last_print) >= config.STATUS_PRINT_MS:
                last_print = now
                print("Estado:", controller.state,
                      "| presencia:", status.get("pir"),
                      "| agua disponible:", status.get("water_available"),
                      "| peso g:", status.get("weight_g"),
                      "| temperatura C:", status.get("temperature_c"),
                      "| humedad %:", status.get("humidity_pct"))
            time.sleep_ms(25)
    except KeyboardInterrupt:
        print("\nParada solicitada desde Thonny.")
    finally:
        if dashboard:
            dashboard.close()
        mqtt_link.close()
        controller.safe_shutdown()
        print("Salidas apagadas; puedes volver a ejecutar main.py.")


main()
