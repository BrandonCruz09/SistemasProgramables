# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: mqtt_camera.py
# Objetivo: Recibir JPEG por MQTT sin acumular cuadros antiguos.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; software en PC.
# ============================================
"""Fuente JPEG por MQTT compatible con el consumidor de video existente."""
import threading
import time
import uuid
import paho.mqtt.client as mqtt


class MQTTCameraStream:
    def __init__(self, settings):
        self.settings = settings
        self.topic = settings.get('frame_topic', 'petcare/equipo8/cam/frame')
        self.condition = threading.Condition()
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.sequence = 0
        self.jpeg = None
        self.received_at = 0
        self.error = 'Esperando imagen por MQTT'
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                 client_id='petcare-cam-pc-' + uuid.uuid4().hex[:8], clean_session=True)
        if settings.get('username'):
            self.client.username_pw_set(settings['username'], settings.get('password', ''))
        self.client.on_connect = self._connect
        self.client.on_subscribe = lambda *args: self.ready.set()
        self.client.on_message = self._message
        self.client.on_disconnect = self._disconnect

    def _connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(self.topic, qos=0)

    def _disconnect(self, *args):
        self.ready.clear()
        with self.condition:
            self.jpeg = None
            self.error = 'Broker desconectado'
            self.condition.notify_all()

    def _message(self, client, userdata, message):
        data = message.payload
        if (message.topic != self.topic or message.retain or not 4 <= len(data) <= 200000
                or not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9')):
            return
        with self.condition:
            self.jpeg = bytes(data)
            self.sequence += 1
            self.received_at = time.monotonic()
            self.error = None
            self.condition.notify_all()

    def start(self):
        self.client.connect_async(self.settings.get('host', '127.0.0.1'),
                                  int(self.settings.get('port', 1883)), keepalive=30)
        self.client.loop_start()

    def latest(self, after=0, timeout=1):
        with self.condition:
            self.condition.wait_for(lambda: self.sequence != after or self.stop_event.is_set(), timeout)
            error = self.error
            if self.jpeg and time.monotonic() - self.received_at > 4:
                error = 'No llegaron frames MQTT recientes'
            return self.sequence, self.jpeg, self.received_at, error

    def stop(self):
        self.stop_event.set()
        self.client.disconnect()
        self.client.loop_stop()
        with self.condition:
            self.condition.notify_all()
