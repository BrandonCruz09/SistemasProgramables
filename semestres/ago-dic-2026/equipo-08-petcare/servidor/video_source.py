# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: video_source.py
# Objetivo: Recibir un unico flujo de la ESP32-CAM y recuperar desconexiones.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; red local.
# ============================================
import threading
import time
from urllib.parse import urlsplit
import requests

MAX_JPEG_BYTES = 250000


def jpeg_frames(chunks, limit=MAX_JPEG_BYTES):
    buffer = bytearray()
    for chunk in chunks:
        buffer.extend(chunk)
        while True:
            start = buffer.find(b'\xff\xd8')
            if start < 0:
                buffer[:] = buffer[-1:]
                break
            if start:
                del buffer[:start]
            end = buffer.find(b'\xff\xd9', 2)
            if end < 0:
                if len(buffer) > limit:
                    raise ValueError('El cuadro supera el limite permitido')
                break
            if end + 2 > limit:
                raise ValueError('JPEG demasiado grande')
            jpeg = bytes(buffer[:end+2])
            del buffer[:end+2]
            yield jpeg


class CameraStream:
    def __init__(self, url):
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            raise ValueError('Configura camera_stream_url con la IP de la camara y /stream')
        self.url = url
        self.stop_event = threading.Event()
        self.condition = threading.Condition()
        self.sequence = 0
        self.jpeg = None
        self.received_at = 0
        self.error = 'Esperando camara'
        self.thread = threading.Thread(target=self._receive, name='camara', daemon=True)

    def start(self):
        self.thread.start()

    def _receive(self):
        with requests.Session() as session:
            session.trust_env = False
            while not self.stop_event.is_set():
                try:
                    with session.get(self.url, stream=True, timeout=(3, 4)) as response:
                        response.raise_for_status()
                        if 'multipart/x-mixed-replace' not in response.headers.get('Content-Type', '').lower():
                            raise ValueError('La camara no entrega MJPEG; revisa /stream y el firmware')
                        for jpeg in jpeg_frames(response.iter_content(4096)):
                            if self.stop_event.is_set():
                                return
                            with self.condition:
                                self.jpeg = jpeg
                                self.sequence += 1
                                self.received_at = time.monotonic()
                                self.error = None
                                self.condition.notify_all()
                        if not self.stop_event.is_set():
                            raise OSError('La camara cerro el video')
                except Exception as error:
                    with self.condition:
                        self.error = str(error)
                        self.jpeg = None
                        self.condition.notify_all()
                    self.stop_event.wait(2)

    def latest(self, after=0, timeout=1):
        with self.condition:
            self.condition.wait_for(lambda: self.sequence != after or self.stop_event.is_set(), timeout)
            return self.sequence, self.jpeg, self.received_at, self.error

    def stop(self):
        self.stop_event.set()
        with self.condition:
            self.condition.notify_all()
        self.thread.join(timeout=8)
