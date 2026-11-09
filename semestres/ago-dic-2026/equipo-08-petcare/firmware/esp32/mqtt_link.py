# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: mqtt_link.py
# Objetivo: Publicar telemetría y procesar comandos MQTT con confirmación.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare - telemetria y comandos MQTT opcionales para MicroPython.
# Requiere umqtt.simple. La conexion se omite si MQTT_HOST queda vacio.
import time
import config
try:
    import ujson as json
except ImportError:
    import json


class MQTTLink:
    def __init__(self):
        self.client = None
        self.pending_command = None
        self.last_command_id = None
        self.last_connect = None
        self.last_publish = None
        self.disabled_message_printed = False
        self.base = getattr(config, "MQTT_BASE_TOPIC", "petcare/equipo8")
        self.telemetry_topic = (self.base + "/telemetry").encode()
        self.command_topic = (self.base + "/commands").encode()
        self.ack_topic = (self.base + "/ack").encode()

    @staticmethod
    def _elapsed(now, then):
        return 999999 if then is None else time.ticks_diff(now, then)

    def _on_message(self, topic, message):
        if topic != self.command_topic:
            return
        try:
            data = json.loads(message.decode())
            if isinstance(data, dict) and data.get("action") in ("feed", "water", "stop_water", "signal_dog"):
                self.pending_command = data
        except Exception:
            print("MQTT: comando JSON invalido; ignorado")

    def _connect(self, now):
        self.last_connect = now
        try:
            from umqtt.simple import MQTTClient
            client = MQTTClient(
                config.MQTT_CLIENT_ID.encode(), config.MQTT_HOST,
                port=config.MQTT_PORT,
                user=config.MQTT_USER.encode() if config.MQTT_USER else None,
                password=config.MQTT_PASSWORD.encode() if config.MQTT_USER else None,
                keepalive=30
            )
            client.set_callback(self._on_message)
            client.connect(timeout=3)
            client.subscribe(self.command_topic)
            self.client = client
            self.last_publish = None
            print("MQTT conectado a %s:%s" % (config.MQTT_HOST, config.MQTT_PORT))
        except Exception as exc:
            self._drop()
            print("MQTT no disponible; PetCare local sigue funcionando:", exc)

    def _drop(self):
        client = self.client
        self.client = None
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                pass

    def _publish_ack(self, command_id, action, ok, message, state):
        payload = {"id": command_id, "action": action, "ok": bool(ok),
                   "message": str(message), "state": state}
        self.client.publish(self.ack_topic, json.dumps(payload).encode())

    def _run_command(self, controller, now):
        command = self.pending_command
        self.pending_command = None
        if not command or self.client is None:
            return
        command_id = str(command.get("id", ""))[:64]
        action = command.get("action")
        if not command_id:
            self._publish_ack("", action, False, "Falta id unico", controller.state)
            return
        if command_id == self.last_command_id:
            self._publish_ack(command_id, action, False, "Comando duplicado; no se repitio", controller.state)
            return
        self.last_command_id = command_id
        try:
            if action == "feed":
                ok, message = controller.request_feed(now)
            elif action == "water":
                ok, message = controller.request_pump(now)
            elif action == "stop_water":
                controller.stop_pump()
                ok, message = True, "Orden de detener bomba aplicada"
            elif action == 'signal_dog':
                ok, message = controller.request_signal(now)
            else:
                ok, message = False, "Accion no permitida"
            self._publish_ack(command_id, action, ok, message, controller.state)
            print("MQTT comando:", command_id, action, "OK" if ok else "rechazado")
        except Exception as exc:
            self._publish_ack(command_id, action, False, "Error al aplicar comando: " + str(exc), controller.state)

    def poll(self, now, controller):
        if not getattr(config, "MQTT_HOST", ""):
            if not self.disabled_message_printed:
                print("MQTT desactivado: completa MQTT_HOST en config.py para usar el puente PC.")
                self.disabled_message_printed = True
            return
        retry_ms = getattr(config, "MQTT_RETRY_SECONDS", 10) * 1000
        if self.client is None:
            if self._elapsed(now, self.last_connect) >= retry_ms:
                self._connect(now)
            return
        try:
            self.client.check_msg()
            self._run_command(controller, now)
            interval = getattr(config, "MQTT_TELEMETRY_SECONDS", 10) * 1000
            if self._elapsed(now, self.last_publish) >= interval:
                payload = {"device": "esp32-devkit", "uptime_ms": now,
                           "status": controller.snapshot()}
                self.client.publish(self.telemetry_topic, json.dumps(payload).encode())
                self.last_publish = now
        except Exception as exc:
            print("MQTT desconectado; se intentara reconectar:", exc)
            self._drop()

    def close(self):
        self._drop()
