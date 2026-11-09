# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: esp32_simulado.py
# Objetivo: Probar la FSM real con sensores y salidas simulados por MQTT.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No se accede a GPIO ni puertos serie; simulacion en PC.
# ============================================
import json
import queue
import sys
import threading
import time
from pathlib import Path
import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'firmware/esp32'))
from controlador import PetCareController


class SensoresSimulados:
    def __init__(self):
        self.values = {'calibrated': True, 'weight_g': 75.0, 'water_available': True,
                       'temperature_c': 24.5, 'humidity_pct': 55.0, 'pir': True,
                       'hx_ok': True, 'dht_ok': True}

    def read(self, now):
        return dict(self.values)


class SalidaSimulada:
    def __init__(self):
        self.active = False
        self.angles = []
        self.releases = 0
        self.color = 'off'

    def on(self): self.active = True
    def off(self): self.active = False
    def move_to(self, angle): self.angles.append(angle)
    def release(self): self.releases += 1
    def set_color(self, color): self.color = color


class ESP32Simulado:
    def __init__(self, topic):
        if '/simulacion/' not in topic:
            raise ValueError('Usa un topico separado con /simulacion/')
        self.topic = topic
        self.sensors = SensoresSimulados()
        self.servo, self.pump, self.buzzer, self.led = [SalidaSimulada() for _ in range(4)]
        self.controller = PetCareController(self.sensors, self.servo, self.pump, self.buzzer, self.led)
        self.commands = queue.Queue(maxsize=100)
        self.ready = threading.Event()
        self.seen = set()
        self.acks = []
        self.last_publish = 0
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='sim-'+topic.split('/')[-1])
        self.client.on_connect = self.on_connect
        self.client.on_subscribe = lambda *args: self.ready.set()
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(self.topic+'/commands', qos=1)

    def on_message(self, client, userdata, message):
        try:
            data = json.loads(message.payload)
            if isinstance(data, dict): self.commands.put_nowait(data)
        except (ValueError, queue.Full):
            pass

    def connect(self, host, port):
        self.client.connect(host, port, 30)
        self.client.loop_start()
        if not self.ready.wait(5):
            self.close()
            raise TimeoutError('El simulador no logro suscribirse a MQTT')

    def tick(self):
        now = int(time.monotonic()*1000)
        self.controller.tick(now)
        while not self.commands.empty():
            data = self.commands.get_nowait()
            cid, action = str(data.get('id','')), data.get('action')
            if not cid or action not in ('feed','water','stop_water','signal_dog'):
                ok, message = False, 'Orden invalida'
            elif cid in self.seen:
                ok, message = False, 'Comando duplicado; no se repitio'
            else:
                self.seen.add(cid)
                if action == 'feed': ok, message = self.controller.request_feed(now)
                elif action == 'water': ok, message = self.controller.request_pump(now)
                elif action == 'signal_dog': ok, message = self.controller.request_signal(now)
                else:
                    self.controller.stop_pump()
                    ok, message = True, 'Orden de detener bomba aplicada'
            ack = {'id':cid, 'action':action, 'ok':ok, 'message':message,
                   'state':self.controller.state, 'simulated':True}
            self.acks.append(ack)
            self.client.publish(self.topic+'/ack', json.dumps(ack), qos=1)
        if time.monotonic()-self.last_publish >= 1:
            self.last_publish = time.monotonic()
            self.publish()

    def publish(self):
        payload = {'device':'esp32-simulado-pc', 'simulated':True,
                   'uptime_ms':int(time.monotonic()*1000), 'status':self.controller.snapshot()}
        self.client.publish(self.topic+'/telemetry', json.dumps(payload), qos=1)

    def close(self):
        self.controller.safe_shutdown()
        self.client.disconnect()
        self.client.loop_stop()
