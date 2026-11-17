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
from pantalla_peso import PantallaPeso


def main(prueba_periodica=False):
    print("\nPetCare | Equipo 08")
    for name in config.TEAM:
        print(" - " + name)
    print("Iniciando en modo seguro: bomba apagada y servo sin PWM.")

    # Apagar primero la bomba, aun si despues falla otro componente.
    pump = PumpRelay()
    controller = dashboard = mqtt_link = None
    servo = buzzer = led = None
    screen = None
    try:
        sensors = SensorHub()
        servo = ServoSG90()
        if prueba_periodica:
            from prueba_periodica import BuzzerOmitido
            buzzer = BuzzerOmitido()
        else:
            buzzer = ActiveBuzzer()
        led = RGBLed()
        controller = PetCareController(sensors, servo, pump, buzzer, led)
        screen = PantallaPeso()
        mqtt_link = MQTTLink()
        mqtt_link.accept_actions = not prueba_periodica
        _wlan, _ip = connect_wifi()
        if _ip:
            dashboard = WebDashboard()
            dashboard.start()
        print('Agua manual supervisada: sin sensor de nivel y sin volumen calibrado.')
        if config.CALIBRATION_ERROR:
            print('Alimento bloqueado: falta calibracion valida.', config.CALIBRATION_ERROR)
        else:
            print('Pesa en gramos. Referencia aproximada:', config.CALIBRATION_APPROXIMATE)
        print('Ctrl+C para salir.')
        last_print = time.ticks_ms()
        plan = None
        if prueba_periodica:
            from prueba_periodica import PruebaPeriodica
            controller.tick(last_print)
            plan = PruebaPeriodica(controller, last_print)
        while True:
            now = time.ticks_ms()
            status = controller.tick(now)
            if plan:
                plan.tick(time.ticks_ms())
            if dashboard:
                dashboard.poll(controller, allow_actions=not prueba_periodica)
            if _wlan is not None and _wlan.isconnected():
                mqtt_link.poll(time.ticks_ms(), controller)
            # La bomba conserva su ultima lectura y lo indica en la pantalla.
            screen.update(status, controller.state, time.ticks_ms())
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
            if screen: screen.close()
            if dashboard: dashboard.close()
            if mqtt_link: mqtt_link.close()
        print('Salidas apagadas.')


if __name__ == '__main__':
    main()
