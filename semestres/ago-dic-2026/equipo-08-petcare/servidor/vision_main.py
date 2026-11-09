# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: vision_main.py
# Objetivo: Coordinar camara, deteccion y pagina de PetCare.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; ejecutado en PC.
# ============================================
import argparse
import json
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit
import cv2
import numpy as np
from detector import DogPersonDetector
from video_source import CameraStream
from mqtt_camera import MQTTCameraStream
from video_web import VideoState, create_server


class VisionWorker:
    def __init__(self, camera, detector, state):
        self.camera = camera
        self.detector = detector
        self.state = state
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name='deteccion', daemon=True)

    def run(self):
        sequence = 0
        previous_received = 0
        count = 0
        started = time.monotonic()
        while not self.stop_event.is_set():
            number, jpeg, received, error = self.camera.latest(sequence, timeout=.5)
            if error or not jpeg or time.monotonic()-received > 4:
                self.detector.presence.reset()
                self.state.unavailable(error or 'Camara sin imagen reciente')
                self.stop_event.wait(.2)
                continue
            if number == sequence:
                continue
            sequence = number
            try:
                if received - previous_received > 4:
                    self.detector.presence.reset()
                previous_received = received
                frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    raise ValueError('Imagen JPEG no valida')
                annotated, result = self.detector.analyze(frame)
                ok, encoded = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not ok:
                    raise ValueError('No se pudo preparar el video')
                count += 1
                elapsed = time.monotonic() - started
                result.update(fps=round(count/max(elapsed, .001), 2),
                              frame_number=number, source='esp32-cam',
                              processing_ms=round(1000*(time.monotonic()-received), 1))
                self.state.update(encoded.tobytes(), result, received)
                if elapsed > 10:
                    count = 0
                    started = time.monotonic()
            except Exception as error:
                self.detector.presence.reset()
                self.state.unavailable('Error de deteccion: ' + str(error))
                self.stop_event.wait(.5)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)


def local_address(camera_url):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect((urlsplit(camera_url).hostname, 80))
            return sock.getsockname()[0]
    except OSError:
        return 'IP_DE_LA_PC'


def main():
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=folder/'server_config.json')
    args = parser.parse_args()
    if not args.config.exists():
        raise SystemExit('Copia server_config.example.json como server_config.json y configura la IP de la camara.')
    settings = json.loads(args.config.read_text(encoding='utf-8-sig'))
    vision = settings.get('vision', {})
    url = settings.get('camera_stream_url', '')
    cv2.setNumThreads(2)
    detector = DogPersonDetector(folder/'models', vision.get('confidence', .55),
                                vision.get('confirm_frames', 3), vision.get('bowl_zone'),
                                vision.get('class_thresholds'))
    transport = settings.get('camera_transport', 'http')
    if transport not in ('http', 'mqtt'):
        raise ValueError('camera_transport debe ser http o mqtt')
    camera = MQTTCameraStream(settings.get('mqtt', {})) if transport == 'mqtt' else CameraStream(url)
    state = VideoState()
    worker = VisionWorker(camera, detector, state)
    web = settings.get('web', {})
    stop_file = folder / 'detener_video.flag'
    stop_file.unlink(missing_ok=True)
    host, port = web.get('host', '0.0.0.0'), int(web.get('port', 8765))
    server = create_server(state, host, port, folder.parent/'interfaz/index.html')
    http_thread = threading.Thread(target=server.serve_forever, name='web', daemon=True)
    camera.start()
    worker.start()
    http_thread.start()
    print('PetCare: http://%s:%d/' % (local_address(url), server.server_port), flush=True)
    print('Abre esa direccion en el celular conectado al mismo Wi-Fi.', flush=True)
    print('Ctrl+C detiene el servidor. Las detecciones no accionan la compuerta.', flush=True)
    print('Entrada de imagen:', transport, '| La respuesta LED requiere iniciar tambien mqtt_bridge.py.', flush=True)
    try:
        while http_thread.is_alive():
            if stop_file.exists():
                break
            time.sleep(.3)
    except KeyboardInterrupt:
        print('Cerrando PetCare...', flush=True)
    finally:
        server.stopping.set()
        with state.condition:
            state.condition.notify_all()
        server.shutdown()
        server.server_close()
        worker.stop()
        camera.stop()
        http_thread.join(timeout=3)
        stop_file.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
