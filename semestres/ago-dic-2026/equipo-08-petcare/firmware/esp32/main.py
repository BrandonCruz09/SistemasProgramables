# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: main.py
# Objetivo: Inicializar módulos y ejecutar el ciclo de supervisión con apagado al detener.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo MG995=33, bomba rele=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare | Equipo 08 | Sistemas Programables
# Objetivo: supervisar sensores y accionar una compuerta con servo posicional y una bomba con rele.
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo=33,
# rele bomba=23, buzzer=22, LED RGB=16/17/21. Ver CONEXIONES_PROTOTIPO.txt.

import time
import config
from sensores import SensorHub
from actuadores import ServoSG90, PumpRelay, ActiveBuzzer, RGBLed
from controlador import PetCareController
from wifi_panel import connect_wifi, WebDashboard
from mqtt_link import MQTTLink


def main():
    print("\nPetCare | Equipo 08")
    for name in config.TEAM:
        print(" - " + name)
    print("Iniciando en modo seguro: bomba apagada y servo sin PWM.")

    # Apagar primero la bomba, aun si despues falla otro componente.
    pump = PumpRelay()
    controller = dashboard = mqtt_link = None
    servo = buzzer = led = None
    try:
        sensors = SensorHub()
        servo = ServoSG90()
        buzzer = ActiveBuzzer()
        led = RGBLed()
        controller = PetCareController(sensors, servo, pump, buzzer, led)
        mqtt_link = MQTTLink()
        _wlan, _ip = connect_wifi()
        if _ip:
            dashboard = WebDashboard()
            dashboard.start()
        print('Agua manual supervisada: sin sensor de nivel y sin volumen calibrado.')
        print('Alimento bloqueado hasta calibrar la pesa. Ctrl+C para salir.')
        last_print = time.ticks_ms()
        while True:
            now = time.ticks_ms()
            status = controller.tick(now)
            if dashboard:
                dashboard.poll(controller)
            mqtt_link.poll(time.ticks_ms(), controller)
            if time.ticks_diff(now, last_print) >= config.STATUS_PRINT_MS:
                last_print = now
                print('Estado:', controller.state, '| PIR:', status.get('pir'),
                      '| RAW:', status.get('raw'), '| peso g:', status.get('weight_g'),
                      '| temperatura:', status.get('temperature_c'),
                      '| humedad:', status.get('humidity_pct'), '| agua: no medida')
            time.sleep_ms(25)
    except KeyboardInterrupt:
        print('Parada solicitada desde Thonny.')
    finally:
        # Primero las salidas; despues la red, que podria tardar en cerrar.
        pump.off()
        try:
            if controller:
                controller.safe_shutdown()
            else:
                if servo: servo.release()
                if buzzer: buzzer.off()
                if led: led.set_color('off')
        finally:
            if dashboard: dashboard.close()
            if mqtt_link: mqtt_link.close()
        print('Salidas apagadas.')


main()
