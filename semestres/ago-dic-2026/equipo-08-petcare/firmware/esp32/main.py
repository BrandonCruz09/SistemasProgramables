# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: main.py
# Objetivo: Inicializar módulos y ejecutar el ciclo de supervisión con apagado al detener.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo MG995=33, bomba rele=23, buzzer=22
# ============================================
# PetCare | Equipo 08 | Sistemas Programables
# Objetivo: supervisar sensores y accionar una compuerta con servo posicional y una bomba con rele.
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, sin flotador, servo=33,
# rele bomba=23, buzzer=22. Ver CONEXIONES_PROTOTIPO.txt.

import time
import config
from sensores import SensorHub
from actuadores import ServoSG90, PumpRelay, ActiveBuzzer
from controlador import PetCareController
from wifi_panel import connect_wifi, WebDashboard
from mqtt_link import MQTTLink
from pantalla_peso import PantallaPeso


def intentar_cierre(name, action):
    try:
        action()
    except Exception as exc:
        print('Error al detener', name, repr(exc))


def main(prueba_periodica=False, solo_lectura=False, max_runtime_ms=None):
    if solo_lectura and prueba_periodica:
        raise ValueError('El diagnostico de sensores no admite ciclos de actuadores')
    print("\nPetCare | Equipo 08")
    for name in config.TEAM:
        print(" - " + name)
    print("Iniciando en modo seguro: bomba apagada y servo sin PWM.")

    # Apagar primero la bomba, aun si despues falla otro componente.
    pump = PumpRelay()
    controller = dashboard = mqtt_link = None
    servo = buzzer = None
    screen = None
    try:
        sensors = SensorHub()
        servo = ServoSG90()
        if prueba_periodica or not config.BUZZER_ENABLED:
            from prueba_periodica import BuzzerOmitido
            buzzer = BuzzerOmitido()
        else:
            buzzer = ActiveBuzzer()
        controller = PetCareController(sensors, servo, pump, buzzer)
        controller.actions_allowed = not solo_lectura
        screen = PantallaPeso()
        mqtt_link = MQTTLink()
        mqtt_link.accept_actions = not (prueba_periodica or solo_lectura)
        _wlan, _ip = connect_wifi()
        if _ip:
            dashboard = WebDashboard()
            try:
                dashboard.start()
            except Exception as exc:
                print('Panel no disponible; sensores continuan:', repr(exc))
                intentar_cierre('panel', dashboard.close)
                dashboard = None
        print('Agua manual supervisada: sin sensor de nivel y sin volumen calibrado.')
        if config.CALIBRATION_ERROR:
            print('Alimento bloqueado: falta calibracion valida.', config.CALIBRATION_ERROR)
        else:
            print('Pesa en gramos. Referencia aproximada:', config.CALIBRATION_APPROXIMATE)
        print('Ctrl+C para salir.')
        last_print = time.ticks_ms()
        started = last_print
        network_retry = last_print
        plan = None
        if prueba_periodica:
            from prueba_periodica import PruebaPeriodica
            controller.tick(last_print)
            plan = PruebaPeriodica(controller, last_print)
        while True:
            now = time.ticks_ms()
            try:
                status = controller.tick(now)
            except Exception as exc:
                controller._actuator_fault('Error de control: ' + repr(exc))
                status = controller.snapshot()
            if plan:
                plan.tick(time.ticks_ms())
            moving = controller.action_in_progress()
            # No hacer operaciones de red durante plazos de servo o bomba.
            if not moving and time.ticks_diff(now, network_retry) >= 0:
                try:
                    if dashboard:
                        dashboard.poll(controller, allow_actions=not (prueba_periodica or solo_lectura))
                    if not controller.action_in_progress() and _wlan is not None and _wlan.isconnected():
                        mqtt_link.poll(time.ticks_ms(), controller)
                except Exception as exc:
                    print('Red: reintento en 10 s; sensores continuan:', repr(exc))
                    network_retry = time.ticks_add(now, 10000)
            moving = controller.action_in_progress()
            # Recalcular: una orden web/MQTT puede haber iniciado una accion.
            if not moving:
                controller._optional('OLED', screen.update, status, controller.state, time.ticks_ms())
            if not moving and time.ticks_diff(now, last_print) >= config.STATUS_PRINT_MS:
                last_print = now
                print('Estado:', controller.state, '| PIR:', status.get('pir'),
                      '| RAW:', status.get('raw'), '| peso g:', status.get('weight_g'),
                      '| temperatura:', status.get('temperature_c'),
                      '| humedad:', status.get('humidity_pct'), '| agua: no medida')
                if not status.get('dht_ok'):
                    print('DHT:', status.get('dht_error') or 'esperando primera lectura')
                if not status.get('hx_ok'):
                    print('Pesa:', status.get('hx_error') or status.get('sensor_error'))
            if max_runtime_ms is not None and time.ticks_diff(now, started) >= max_runtime_ms:
                print('Comprobacion de tiempo limitado terminada.')
                break
            time.sleep_ms(25)
    except KeyboardInterrupt:
        print('Parada solicitada desde Thonny.')
    except Exception as exc:
        print('Fallo del programa; se detienen salidas:', repr(exc))
        import sys
        sys.print_exception(exc)
    finally:
        # Primero las salidas; despues la red, que podria tardar en cerrar.
        intentar_cierre('bomba', pump.off)
        if controller:
            intentar_cierre('controlador', controller.safe_shutdown)
        if servo: intentar_cierre('servo', servo.release)
        if buzzer: intentar_cierre('buzzer', buzzer.off)
        if screen: intentar_cierre('OLED', screen.close)
        if dashboard: intentar_cierre('panel', dashboard.close)
        if mqtt_link: intentar_cierre('MQTT', mqtt_link.close)
        print('Salidas apagadas.')


if __name__ == '__main__':
    main()
