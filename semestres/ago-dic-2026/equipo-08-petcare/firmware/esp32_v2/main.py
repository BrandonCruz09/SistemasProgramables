"""Programa integrado: sin tara ni movimientos al iniciar."""

import time
import config


def run_service(control, name, action):
    """Un fallo de red o pantalla no interrumpe el control de las salidas."""
    key = "servicio_" + name
    try:
        result = action()
        control.errors.pop(key, None)
        return result
    except Exception as exc:
        message = repr(exc)
        if control.errors.get(key) != message:
            print(name + ":", message)
        control.errors[key] = message
        return None


def cleanup(resources):
    """Intenta cada parada aunque falle otra; no confirma el resultado fisico."""
    for name, action in resources:
        try:
            action()
        except Exception as exc:
            print("Parada " + name + ":", repr(exc))


def main(solo_lectura=False, max_runtime_ms=None):
    from actuadores import ServoSG90, PumpRelay, ActiveBuzzer
    from sensores import SensorHub
    from controlador import PetCareController
    from mqtt_link import MQTTLink
    from wifi_panel import Wifi, WebDashboard
    from pantalla_peso import PantallaPeso

    resources = []
    try:
        pump = PumpRelay()
        resources.append(("bomba", pump.off))
        servo = ServoSG90()
        resources.append(("servo", servo.release))
        buzzer = ActiveBuzzer()
        resources.append(("buzzer", buzzer.off))
        control = PetCareController(SensorHub(), servo, pump, buzzer)
        control.actions_allowed = not solo_lectura
        mqtt = MQTTLink()
        resources.append(("MQTT", mqtt.close))
        wifi = Wifi()
        web = WebDashboard()
        resources.append(("panel", web.close))
        screen = PantallaPeso()
        start = time.ticks_ms()
        last_print = web_retry = start
        print("\nPetCare", config.VERSION, "| GPIO conservados")
        print("Calibracion:", control.sensors.cal)
        print("Servo:", config.SERVO_OPEN_US, "/", config.SERVO_CLOSED_US, "us")
        print("No hay tara automatica. Ctrl+C solicita apagar las salidas.")

        while True:
            now = time.ticks_ms()
            try:
                status = control.tick(now)
            except Exception as exc:
                control.handle_fault(exc, now)
                status = control.snapshot()
            run_service(
                control,
                "wifi",
                lambda: wifi.tick(time.ticks_ms(), not control.action_in_progress()),
            )
            connected = run_service(control, "conexion", wifi.connected)
            run_service(
                control, "mqtt", lambda: mqtt.poll(time.ticks_ms(), control, bool(connected))
            )
            if connected and web.server is None and time.ticks_diff(now, web_retry) >= 0:
                web_retry = time.ticks_add(now, 15000)
                try:
                    web.start()
                    print("Panel local: http://" + wifi.wlan.ifconfig()[0] + "/")
                    control.errors.pop("servicio_panel_inicio", None)
                except Exception as exc:
                    control.errors["servicio_panel_inicio"] = repr(exc)
                    run_service(control, "panel_cierre", web.close)
            run_service(control, "panel", lambda: web.poll(control, time.ticks_ms()))
            if not control.action_in_progress():
                run_service(
                    control,
                    "pantalla",
                    lambda: screen.update(status, control.state, time.ticks_ms()),
                )
            if time.ticks_diff(now, last_print) >= 3000:
                last_print = now
                print(
                    "RAW:",
                    status.get("raw"),
                    "| g:",
                    status.get("weight_g"),
                    "| DHT:",
                    status.get("temperature_c"),
                    status.get("humidity_pct"),
                    "| PIR:",
                    status.get("pir"),
                    "|",
                    control.state,
                )
            if max_runtime_ms is not None and time.ticks_diff(now, start) >= max_runtime_ms:
                break
            time.sleep_ms(10)
    except KeyboardInterrupt:
        print("Detenido por el usuario")
    finally:
        cleanup(resources)
        print("Parada solicitada; calibracion sin modificar")


if __name__ == "__main__":
    main()
