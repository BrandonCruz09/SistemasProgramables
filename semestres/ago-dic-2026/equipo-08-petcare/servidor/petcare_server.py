# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: petcare_server.py
# Objetivo: Puente MQTT/OpenCV/Firebase con Firestore o RTDB.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica: ejecutado en PC.
# ============================================
# PetCare | Equipo 08 | Puente MQTT + OpenCV + Firebase Realtime Database
# Corre en la computadora, no en la ESP32. Recibe telemetria MQTT, consulta la
# servidor de vision por HTTP y sincroniza estado/comandos con Firebase.
from __future__ import annotations
import json
import queue
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from ia_policy import DogSignalPolicy
from dashboard import DashboardState, start_dashboard

BASE_TOPIC = "petcare/equipo8"
TELEMETRY_PATH = "petcare/equipo8/latest"
VISION_PATH = "petcare/equipo8/vision"
COMMAND_PATH = "petcare/equipo8/command"
EVENTS_PATH = "petcare/equipo8/events"
ALLOWED_COMMANDS = {"feed", "water", "stop_water"}


def sanitize_command(data):
    """Devuelve (id, action) solo para ordenes conocidas y con id."""
    if not isinstance(data, dict):
        return None
    command_id = str(data.get("id", "")).strip()[:64]
    action = data.get("action")
    if not command_id or not isinstance(action, str) or action not in ALLOWED_COMMANDS:
        return None
    return command_id, action


def movement_detected(changed_percent, threshold_percent=1.8):
    """Umbral simple; mide movimiento en imagen, no identifica si es un perro."""
    try:
        return float(changed_percent) >= float(threshold_percent)
    except (TypeError, ValueError):
        return False


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class FirebaseREST:
    """REST client con Firebase Anonymous Auth y refresh token local excluido."""
    def __init__(self, settings, folder):
        import requests
        self.requests = requests
        self.db_url = settings.get("database_url", "").rstrip("/")
        self.api_key = settings.get("api_key", "")
        self.session = requests.Session()
        self.token_file = Path(folder) / ".firebase_refresh_token"
        self.id_token = None
        self.refresh_token = None
        self.expires_at = 0
        self.uid = None
        if self.token_file.exists():
            self.refresh_token = self.token_file.read_text(encoding="utf-8").strip() or None
        self._ensure_token()

    def _save_refresh(self, value):
        self.refresh_token = value
        self.token_file.write_text(value, encoding="utf-8")

    def _ensure_token(self, force=False):
        if self.id_token and not force and time.time() < self.expires_at - 60:
            return
        if self.refresh_token:
            response = self.session.post(
                "https://securetoken.googleapis.com/v1/token",
                params={"key": self.api_key},
                data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
                timeout=10,
            )
            if response.ok:
                token = response.json()
                self.id_token = token["id_token"]
                self.uid = token.get("user_id")
                self._save_refresh(token.get("refresh_token", self.refresh_token))
                self.expires_at = time.time() + int(token.get("expires_in", 3600))
                return
            self.refresh_token = None
        response = self.session.post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signUp",
            params={"key": self.api_key},
            json={"returnSecureToken": True},
            timeout=10,
        )
        if not response.ok:
            raise RuntimeError("Firebase Auth HTTP %s; revisa proveedor y configuracion local" % response.status_code)
        token = response.json()
        self.id_token = token["idToken"]
        self.uid = token.get("localId")
        self._save_refresh(token["refreshToken"])
        self.expires_at = time.time() + int(token.get("expiresIn", 3600))
        print("Firebase: autenticacion anonima lista; UID:", token.get("localId", "(sin UID)"))

    def request(self, method, path, payload=None, query=None):
        self._ensure_token()
        url = self.db_url + "/" + quote(path.strip("/"), safe="/") + ".json"
        response = self.session.request(
            method, url, params={**(query or {}), "auth": self.id_token}, json=payload, timeout=10
        )
        if response.status_code == 401:
            self._ensure_token(force=True)
            response = self.session.request(
                method, url, params={**(query or {}), "auth": self.id_token}, json=payload, timeout=10
            )
        if not response.ok:
            # La URL de requests contiene el token; no incluirla en registros.
            raise RuntimeError("Firebase HTTP %s en %s" % (response.status_code, path))
        if response.content:
            return response.json()
        return None

    def get(self, path):
        return self.request("GET", path)

    def recent(self, path):
        return self.request('GET', path, query={'orderBy':'"$key"','limitToLast':120})

    def put(self, path, payload):
        return self.request("PUT", path, payload)

    def patch(self, path, payload):
        return self.request("PATCH", path, payload)

    def post(self, path, payload):
        return self.request("POST", path, payload)


class MotionDetector:
    """Compara capturas consecutivas QVGA; no almacena ni sube imagenes."""
    def __init__(self, threshold_percent=1.8):
        self.threshold_percent = float(threshold_percent)
        self.previous = None

    def analyze_jpeg(self, jpeg_bytes):
        import cv2
        import numpy as np
        encoded = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
        if frame is None:
            raise ValueError("La ESP32-CAM no envio una imagen JPEG valida")
        frame = cv2.resize(frame, (160, 120), interpolation=cv2.INTER_AREA)
        frame = cv2.GaussianBlur(frame, (5, 5), 0)
        if self.previous is None:
            self.previous = frame
            return {"ready": False, "movement_detected": False, "changed_percent": 0.0}
        delta = cv2.absdiff(self.previous, frame)
        mask = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        changed = 100.0 * cv2.countNonZero(mask) / float(mask.size)
        self.previous = frame
        return {
            "ready": True,
            "movement_detected": movement_detected(changed, self.threshold_percent),
            "changed_percent": round(changed, 2),
        }


class PetCareBridge:
    def __init__(self, settings, firebase=None):
        import requests
        self.requests = requests
        self.settings = settings
        self.firebase = firebase
        self.base_topic = settings.get("mqtt", {}).get("base_topic", BASE_TOPIC).strip("/")
        self.firebase_root = settings.get("firebase_root", "petcare/equipo8").strip("/")
        self.telemetry_path = self.firebase_root + "/latest"
        self.vision_path = self.firebase_root + "/vision"
        self.command_path = self.firebase_root + "/command"
        self.events_path = self.firebase_root + "/events"
        self.camera_url = settings.get("camera_url", "").strip()
        self.vision_url = settings.get("vision_url", "").strip()
        self.camera_interval = max(0.5, float(settings.get("camera_interval_seconds", 1.5)))
        self.command_interval = max(1.0, float(settings.get("command_interval_seconds", 2)))
        self.motion_interval = max(2.0, float(settings.get("vision_publish_seconds", 10)))
        self.detector = MotionDetector(settings.get("motion_threshold_percent", 1.8))
        self.messages = queue.Queue(maxsize=100)
        self.client = None
        self.last_command_poll = 0
        self.last_camera_poll = 0
        self.last_vision_publish = 0
        self.last_motion_state = None
        self.last_history_write = 0
        self.last_event = None
        self.last_camera_error = 0
        self.last_firebase_error = 0
        self.last_seen_command = None
        self.ia_enabled = settings.get('automation', {}).get('dog_indicator_enabled', False) is True
        self.ia_policy = DogSignalPolicy(settings.get('automation', {}).get('cooldown_seconds', 15))
        self.pending_ia = {}
        self.lecturas_path = self.firebase_root + '/lecturas'
        self.ia_events_path = self.firebase_root + '/eventos_ia'
        self.current_path = self.firebase_root + '/estado_actual'
        self.dashboard = DashboardState()
        self.last_cloud_telemetry = 0
        self.last_cloud_vision = 0
        self.firestore_mode = settings.get('firebase', {}).get('provider') == 'firestore'
        if self.firestore_mode:
            self.command_interval = max(30.0, self.command_interval)

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe([(self.base_topic + "/telemetry", 0), (self.base_topic + "/ack", 0)])
            print("MQTT conectado; escuchando telemetria y confirmaciones.")
        else:
            print("MQTT: el broker rechazo la conexion:", reason_code)

    def _queue_message(self, item):
        try:
            self.messages.put_nowait(item)
        except queue.Full:
            try:
                self.messages.get_nowait()
                self.messages.put_nowait(item)
            except queue.Empty:
                pass

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            self._queue_message((message.topic, payload))
        except Exception as exc:
            print("MQTT: mensaje ignorado:", exc)

    def set_mqtt_client(self, client):
        self.client = client

    def _firebase_call(self, label, method, *args):
        if not self.firebase:
            return None
        try:
            result = getattr(self.firebase, method)(*args)
            with self.dashboard.lock:
                self.dashboard.cloud = {'status':'Última operación Firebase correcta', 'updated_at':utc_now()}
            return result
        except Exception as exc:
            with self.dashboard.lock:
                self.dashboard.cloud = {'status':'Firebase pendiente o sin acceso', 'updated_at':utc_now()}
            now = time.monotonic()
            if now - self.last_firebase_error > 10:
                self.last_firebase_error = now
                print("Firebase", label, "pendiente:", exc)
            return None

    def process_messages(self):
        while True:
            try:
                topic, payload = self.messages.get_nowait()
            except queue.Empty:
                break
            if topic.endswith("/telemetry") and isinstance(payload, dict):
                saved = {"received_at": utc_now(), **payload}
                self.dashboard.update(saved)
                cloud_now = time.monotonic()
                if not self.firestore_mode or cloud_now-self.last_cloud_telemetry >= 60:
                    self.last_cloud_telemetry = cloud_now
                    self._firebase_call("telemetria", "put", self.telemetry_path, saved)
                    self._firebase_call('estado actual', 'patch', self.current_path,
                                        {'telemetria': saved, 'updated_at': utc_now()})
                status = payload.get("status", {})
                if not isinstance(status, dict):
                    status = {}
                event = status.get("last_event")
                now = time.monotonic()
                if (not self.firestore_mode and event and event != self.last_event) or now - self.last_history_write >= 60:
                    self._firebase_call("historial", "post", self.events_path,
                                        {"received_at": utc_now(), "type": "telemetry", "data": saved})
                    self._firebase_call('lectura historica', 'put',
                                        self.lecturas_path + '/' + str(time.time_ns()), saved)
                    self.last_history_write = now
                    self.last_event = event
                print("Telemetria MQTT recibida; estado:", status.get("state", "desconocido"))
            elif topic.endswith("/ack") and isinstance(payload, dict):
                with self.dashboard.lock:
                    self.dashboard.events.append(dict(payload, received_at=utc_now()))
                cid = payload.get('id')
                if isinstance(cid, str) and cid in self.pending_ia:
                    self.pending_ia.pop(cid)
                    self._firebase_call('confirmacion IA', 'patch', self.ia_events_path + '/' + cid,
                                        {'estado': 'confirmado' if payload.get('ok') else 'rechazado',
                                         'ack': payload, 'acknowledged_at': utc_now()})
                    print('IA -> MQTT -> ACK:', cid, payload.get('ok'), payload.get('message', ''))
                current = self._firebase_call("lectura de comando", "get", self.command_path)
                if isinstance(current, dict) and current.get("id") == payload.get("id"):
                    status = "aceptado" if payload.get("ok") else "rechazado"
                    self._firebase_call("confirmacion de comando", "patch", self.command_path,
                                        {"status": status, "result": payload.get("message", ""),
                                         "device_state": payload.get("state", ""),
                                         "acknowledged_at": utc_now()})
                print("Confirmacion del ESP32:", payload.get("id"), payload.get("message", ""))

    def process_vision(self, result):
        """Actuar solo sobre cuadros recientes, sin alimentar por detección."""
        now = time.monotonic()
        for cid, sent in list(self.pending_ia.items()):
            if now - sent >= 5:
                self.pending_ia.pop(cid)
                self._firebase_call('IA sin ACK', 'patch', self.ia_events_path + '/' + cid,
                                    {'estado': 'sin_confirmacion', 'updated_at': utc_now()})
                print('IA sin confirmacion del ESP32:', cid)
        if not self.ia_enabled or not self.client or not self.client.is_connected():
            return None
        command = self.ia_policy.propose(result, now)
        if not command:
            return None
        # QoS0 sin retención: no acumular señales de cámara para dispositivos desconectados.
        sent = self.client.publish(self.base_topic + '/commands', json.dumps(command), qos=0, retain=False)
        if sent.rc != 0:
            return None
        self.ia_policy.accepted(now)
        self.pending_ia[command['id']] = now
        event = {'deteccion': 'dog', 'accion': 'signal_dog', 'confianza': command['confidence'],
                 'timestamp': utc_now(), 'estado': 'enviado', 'command': command,
                 'simulated': '/simulacion/' in self.base_topic}
        self._firebase_call('evento IA', 'put', self.ia_events_path + '/' + command['id'], event)
        print('Frame', command['frame_number'], '-> IA perro -> MQTT signal_dog:', command['id'])
        return command

    def poll_command(self):
        if not self.firebase or not self.client or not self.client.is_connected():
            return
        now = time.monotonic()
        if now - self.last_command_poll < self.command_interval:
            return
        self.last_command_poll = now
        command = self._firebase_call("lectura de comando", "get", self.command_path)
        if not isinstance(command, dict) or command.get("status") != "pendiente":
            return
        parsed = sanitize_command(command)
        if not parsed:
            self._firebase_call("rechazo de comando", "patch", self.command_path,
                                {"status": "rechazado", "result": "id o accion no validos"})
            return
        command_id, action = parsed
        if command_id == self.last_seen_command:
            return
        payload = json.dumps({"id": command_id, "action": action}, separators=(",", ":"))
        result = self.client.publish(self.base_topic + "/commands", payload, qos=1, retain=False)
        if result.rc == 0:
            self.last_seen_command = command_id
            self._firebase_call("estado de comando", "patch", self.command_path,
                                {"status": "enviado", "sent_at": utc_now()})
            print("Orden Firebase -> MQTT:", command_id, action)

    def poll_vision(self):
        now = time.monotonic()
        if now - self.last_camera_poll < self.camera_interval:
            return
        self.last_camera_poll = now
        try:
            response = self.requests.get(self.vision_url, timeout=3)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict) or not isinstance(result.get("available"), bool):
                raise ValueError("Estado de vision no valido")
            # Solo se transfieren resultados; la PC comparte el video por HTTP.
            result.pop("viewers", None)
        except Exception:
            result = {"available": False, "dog_detected": None, "person_detected": None,
                      "dog_in_bowl_zone": None, "detections": [],
                      "error": "Servidor de vision no disponible", "processed_at": utc_now()}
        self.process_vision(result)
        with self.dashboard.lock:
            self.dashboard.vision = result
        key = (result.get("available"), result.get("dog_detected"),
               result.get("person_detected"), result.get("dog_in_bowl_zone"))
        if key != self.last_motion_state or now - self.last_vision_publish >= self.motion_interval:
            self.last_motion_state = key
            self.last_vision_publish = now
            if self.client and self.client.is_connected():
                self.client.publish(self.base_topic + "/vision", json.dumps(result), qos=0, retain=False)
            if not self.firestore_mode or now-self.last_cloud_vision >= 60:
                self.last_cloud_vision = now
                self._firebase_call("vision", "put", self.vision_path, result)
                self._firebase_call('estado vision', 'patch', self.current_path,
                                    {'vision': result, 'updated_at': utc_now()})
            print("Vision: disponible=%s perro=%s persona=%s" % key[:3])

    def poll_camera(self):
        if self.vision_url:
            self.poll_vision()
            return
        if not self.camera_url:
            return
        now = time.monotonic()
        if now - self.last_camera_poll < self.camera_interval:
            return
        self.last_camera_poll = now
        try:
            response = self.requests.get(self.camera_url, timeout=3)
            response.raise_for_status()
            if "image/" not in response.headers.get("Content-Type", ""):
                raise ValueError("La URL no devolvio una imagen; usa el endpoint /foto")
            result = self.detector.analyze_jpeg(response.content)
            if not result["ready"]:
                print("OpenCV: imagen inicial recibida; esperando siguiente cuadro para comparar.")
                return
            result.update({"source": "esp32-cam", "processed_at": utc_now(),
                           "method": "diferencia entre cuadros", "detects_dog": False})
            should_publish = (result["movement_detected"] != self.last_motion_state or
                              now - self.last_vision_publish >= self.motion_interval)
            if should_publish:
                self.last_motion_state = result["movement_detected"]
                self.last_vision_publish = now
                payload = json.dumps(result, separators=(",", ":"))
                if self.client and self.client.is_connected():
                    self.client.publish(self.base_topic + "/vision", payload, qos=0, retain=False)
                self._firebase_call("vision", "put", self.vision_path, result)
                print("OpenCV: movimiento" if result["movement_detected"] else "OpenCV: sin movimiento",
                      "(%.2f%% del cuadro cambiado)" % result["changed_percent"])
        except Exception as exc:
            if now - self.last_camera_error > 10:
                self.last_camera_error = now
                print("OpenCV/camara pendiente:", exc)

    def run(self):
        print("Puente PetCare activo. Ctrl+C detiene el servidor.")
        print("Camara:", self.camera_url or "no configurada")
        print("Firebase:", "conectado" if self.firebase else "sin configurar")
        while True:
            self.process_messages()
            self.poll_command()
            self.poll_camera()
            time.sleep(0.1)


def load_settings(folder):
    path = Path(folder) / "server_config.json"
    if not path.exists():
        example = Path(folder) / "server_config.example.json"
        raise FileNotFoundError("Copia server_config.example.json como server_config.json y completa sus campos.")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    import paho.mqtt.client as mqtt
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=folder / 'server_config.json')
    args = parser.parse_args()
    settings = json.loads(args.config.read_text(encoding='utf-8-sig'))
    mqtt_settings = settings.get("mqtt", {})
    host = mqtt_settings.get("host", "127.0.0.1")
    port = int(mqtt_settings.get("port", 1883))
    firebase_settings = settings.get("firebase", {})
    firebase = None
    if firebase_settings.get("enabled"):
        provider = firebase_settings.get('provider', 'rtdb')
        target = 'project_id' if provider == 'firestore' else 'database_url'
        if not firebase_settings.get(target) or not firebase_settings.get("api_key"):
            print("Firebase omitido: faltan parámetros locales de conexión.")
        else:
            try:
                if provider == 'firestore':
                    from firestore_rest import FirestoreREST
                    firebase = FirestoreREST(firebase_settings, folder)
                elif provider == 'rtdb':
                    firebase = FirebaseREST(firebase_settings, folder)
                else:
                    raise ValueError('Proveedor Firebase desconocido')
            except Exception as exc:
                print("Firebase no disponible; MQTT/OpenCV local continuan:", exc)
    bridge = PetCareBridge(settings, firebase)
    dashboard_server = None
    dashboard_settings = settings.get('dashboard', {})
    if dashboard_settings.get('enabled'):
        if firebase:
            bridge.dashboard.restore_history(bridge._firebase_call('recuperar histórico', 'recent', bridge.lecturas_path))
        dashboard_server = start_dashboard(bridge.dashboard, folder.parent/'interfaz/dashboard.html',
                                          dashboard_settings.get('host','0.0.0.0'), dashboard_settings.get('port',8766))
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="petcare-equipo8-pc")
    client.on_connect = bridge.on_connect
    client.on_message = bridge.on_message
    user = mqtt_settings.get("username", "")
    password = mqtt_settings.get("password", "")
    if user:
        client.username_pw_set(user, password)
    bridge.set_mqtt_client(client)
    print("Conectando al broker MQTT %s:%d ..." % (host, port))
    try:
        client.connect(host, port, keepalive=30)
    except OSError as exc:
        if dashboard_server:
            dashboard_server.shutdown()
            dashboard_server.server_close()
        print("No se pudo conectar al broker MQTT. Inicia Mosquitto y revisa host/puerto:", exc)
        return 2
    client.loop_start()
    try:
        bridge.run()
    except KeyboardInterrupt:
        print("\nCierre solicitado; no se enviaran mas ordenes.")
    finally:
        if dashboard_server:
            dashboard_server.shutdown()
            dashboard_server.server_close()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
