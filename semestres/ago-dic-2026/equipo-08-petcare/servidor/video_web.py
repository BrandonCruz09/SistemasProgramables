# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: video_web.py
# Objetivo: Compartir video procesado y estado con el navegador del celular.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; servidor HTTP en PC.
# ============================================
import copy
import json
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from http_local import LocalHTTPServer
import cv2
import numpy as np


def waiting_image(message='Camara sin conexion'):
    frame = np.full((480, 640, 3), (35, 46, 51), dtype=np.uint8)
    cv2.putText(frame, 'PETCARE', (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (235, 240, 240), 2)
    cv2.putText(frame, message, (40, 255), cv2.FONT_HERSHEY_SIMPLEX, .65, (170, 210, 220), 1)
    return cv2.imencode('.jpg', frame)[1].tobytes()


class VideoState:
    def __init__(self, stale_seconds=4):
        self.condition = threading.Condition()
        self.sequence = 0
        self.jpeg = None
        self.status = {'available': False, 'error': 'Esperando imagen de la camara'}
        self.last_frame = 0
        self.stale_seconds = stale_seconds
        self.waiting = waiting_image()
        self.viewers = 0

    def update(self, jpeg, status, received_at):
        with self.condition:
            self.jpeg = jpeg
            self.last_frame = received_at
            self.status = dict(status, processed_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
            self.sequence += 1
            self.condition.notify_all()

    def unavailable(self, reason):
        with self.condition:
            self.jpeg = None
            self.status = {'available': False, 'error': reason}
            self.condition.notify_all()

    def snapshot(self):
        with self.condition:
            age = time.monotonic() - self.last_frame if self.last_frame else None
            result = copy.deepcopy(self.status)
            result['frame_age_seconds'] = round(age, 2) if age is not None else None
            result['viewers'] = self.viewers
            if not self.jpeg or age is None or age > self.stale_seconds:
                result.update(available=False, dog_detected=None, person_detected=None,
                              dog_in_bowl_zone=None, detections=[])
                result['error'] = result.get('error') or 'No llegaron imagenes recientes'
                return self.sequence, self.waiting, result
            return self.sequence, self.jpeg, result


def create_server(state, host, port, html_path):
    html = Path(html_path).read_bytes()
    slots = threading.BoundedSemaphore(4)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(5)
            super().setup()

        def handle(self):
            try:
                super().handle()
            except (ConnectionResetError, BrokenPipeError, TimeoutError):
                pass

        def log_message(self, format, *args):
            pass

        def reply(self, code, mime, body):
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.connection.settimeout(5)
            path = urlsplit(self.path).path
            try:
                if path == '/':
                    self.reply(200, 'text/html; charset=utf-8', html)
                elif path == '/api/status':
                    self.reply(200, 'application/json', json.dumps(state.snapshot()[2]).encode())
                elif path == '/snapshot.jpg':
                    self.reply(200, 'image/jpeg', state.snapshot()[1])
                elif path == '/stream':
                    self.stream()
                elif path == '/favicon.ico':
                    self.reply(204, 'image/x-icon', b'')
                else:
                    self.reply(404, 'text/plain', b'Ruta no encontrada')
            except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                pass

        def stream(self):
            if not slots.acquire(blocking=False):
                self.reply(503, 'text/plain', b'Hay cuatro visores abiertos. Cierra uno e intenta de nuevo.')
                return
            with state.condition:
                state.viewers += 1
            print('Visor conectado:', self.client_address[0], flush=True)
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                last = -1
                while not self.server.stopping.is_set():
                    with state.condition:
                        state.condition.wait_for(lambda: state.sequence != last or self.server.stopping.is_set(), 1)
                    number, jpeg, _ = state.snapshot()
                    self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n' % len(jpeg))
                    self.wfile.write(jpeg + b'\r\n')
                    self.wfile.flush()
                    last = number
            finally:
                with state.condition:
                    state.viewers -= 1
                slots.release()

    server = LocalHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.stopping = threading.Event()
    return server
