# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: camara_mqtt.py
# Objetivo: Publicar JPEG de la cámara por MQTT con reconexión.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: OV2640 integrada; sin conexión TX/RX al DevKit.
# ============================================
"""Publicar JPEG sin retención; HTTP sigue disponible como alternativa."""
import time
import uasyncio as asyncio


class PublicadorFrames:
    def __init__(self, settings):
        self.settings = settings
        self.client = None
        self.interval = max(500, int(getattr(settings, 'INTERVAL_MS', 700)))
        self.topic = getattr(settings, 'TOPIC', 'petcare/equipo8/cam/frame').encode()

    def cerrar(self):
        client, self.client = self.client, None
        if client:
            try:
                client.disconnect()
            except Exception:
                try:
                    client.sock.close()
                except Exception:
                    pass

    def conectar(self):
        from umqtt.simple import MQTTClient
        s = self.settings
        user = getattr(s, 'USER', '')
        password = getattr(s, 'PASSWORD', '')
        client = MQTTClient(b'petcare-equipo8-cam', s.HOST, port=getattr(s, 'PORT', 1883),
                            user=user.encode() if user else None,
                            password=password.encode() if user else None, keepalive=20)
        self.client = client
        client.connect(timeout=2)
        client.sock.settimeout(2)
        print('MQTT camara conectado; publicando JPEG en', self.topic)

    async def ejecutar(self, capturar):
        try:
            while True:
                try:
                    if self.client is None:
                        self.conectar()
                    jpeg = await capturar()
                    self.client.publish(self.topic, jpeg, qos=0, retain=False)
                    del jpeg
                    await asyncio.sleep_ms(self.interval)
                except Exception as exc:
                    print('MQTT camara: reintento; HTTP sigue disponible:', exc)
                    self.cerrar()
                    await asyncio.sleep(3)
        finally:
            self.cerrar()
