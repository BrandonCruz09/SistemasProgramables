# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: petcare_server.py
# Objetivo: Puente MQTT/OpenCV/Firebase RTDB.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica: ejecutado en PC.
# ============================================
# PetCare | Equipo 08 | Puente MQTT + OpenCV + Firebase Realtime Database
# Corre en la computadora, no en la ESP32. Recibe telemetria MQTT, consulta la
# ESP32-CAM por HTTP, detecta movimiento y sincroniza estado/comandos con Firebase.
from __future__ import annotations
import json
import queue
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

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
        response.raise_for_status()
        token = response.json()
        self.id_token = token["idToken"]
        self._save_refresh(token["refreshToken"])
        self.expires_at = time.time() + int(token.get("expiresIn", 3600))
        print("Firebase: autenticacion anonima lista; UID:", token.get("localId", "(sin UID)"))

    def request(self, method, path, payload=None):
        self._ensure_token()
        url = self.db_url + "/" + quote(path.strip("/"), safe="/") + ".json"
        response = self.session.request(
            method, url, params={"auth": self.id_token}, json=payload, timeout=10
        )
        if response.status_code == 401:
            self._ensure_token(force=True)
            response = self.session.request(
                method, url, params={"auth": self.id_token}, json=payload, timeout=10
            )
        response.raise_for_status()
        if response.content:
            return response.json()
        return None

    def get(self, path):
        return self.request("GET", path)

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
        self.camera_url = settings.get("camera_url", "").strip()
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

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if int(reason_code) == 0:
            client.subscribe([(BASE_TOPIC + "/telemetry", 0), (BASE_TOPIC + "/ack", 0)])
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
            return getattr(self.firebase, method)(*args)
        except Exception as exc:
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
                self._firebase_call("telemetria", "put", TELEMETRY_PATH, saved)
                status = payload.get("status", {})
                if not isinstance(status, dict):
                    status = {}
                event = status.get("last_event")
                now = time.monotonic()
                if (event and event != self.last_event) or now - self.last_history_write >= 60:
                    self._firebase_call("historial", "post", EVENTS_PATH,
                                        {"received_at": utc_now(), "type": "telemetry", "data": saved})
                    self.last_history_write = now
                    self.last_event = event
                print("Telemetria MQTT recibida; estado:", status.get("state", "desconocido"))
            elif topic.endswith("/ack") and isinstance(payload, dict):
                current = self._firebase_call("lectura de comando", "get", COMMAND_PATH)
                if isinstance(current, dict) and current.get("id") == payload.get("id"):
                    status = "aceptado" if payload.get("ok") else "rechazado"
                    self._firebase_call("confirmacion de comando", "patch", COMMAND_PATH,
                                        {"status": status, "result": payload.get("message", ""),
                                         "device_state": payload.get("state", ""),
                                         "acknowledged_at": utc_now()})
                print("Confirmacion del ESP32:", payload.get("id"), payload.get("message", ""))

    def poll_command(self):
        if not self.firebase or not self.client or not self.client.is_connected():
            return
        now = time.monotonic()
        if now - self.last_command_poll < self.command_interval:
            return
        self.last_command_poll = now
        command = self._firebase_call("lectura de comando", "get", COMMAND_PATH)
        if not isinstance(command, dict) or command.get("status") != "pendiente":
            return
        parsed = sanitize_command(command)
        if not parsed:
            self._firebase_call("rechazo de comando", "patch", COMMAND_PATH,
                                {"status": "rechazado", "result": "id o accion no validos"})
            return
        command_id, action = parsed
        if command_id == self.last_seen_command:
            return
        payload = json.dumps({"id": command_id, "action": action}, separators=(",", ":"))
        result = self.client.publish(BASE_TOPIC + "/commands", payload, qos=1, retain=False)
        if result.rc == 0:
            self.last_seen_command = command_id
            self._firebase_call("estado de comando", "patch", COMMAND_PATH,
                                {"status": "enviado", "sent_at": utc_now()})
            print("Orden Firebase -> MQTT:", command_id, action)

    def poll_camera(self):
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
                raise ValueError("La URL no devolvio una imagen; usa el endpoint /capture")
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
                    self.client.publish(BASE_TOPIC + "/vision", payload, qos=0, retain=False)
                self._firebase_call("vision", "put", VISION_PATH, result)
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
    settings = load_settings(folder)
    mqtt_settings = settings.get("mqtt", {})
    host = mqtt_settings.get("host", "127.0.0.1")
    port = int(mqtt_settings.get("port", 1883))
    firebase_settings = settings.get("firebase", {})
    firebase = None
    if firebase_settings.get("enabled"):
        if not firebase_settings.get("database_url") or not firebase_settings.get("api_key"):
            print("Firebase omitido: faltan database_url o api_key en server_config.json.")
        else:
            try:
                firebase = FirebaseREST(firebase_settings, folder)
            except Exception as exc:
                print("Firebase no disponible; MQTT/OpenCV local continuan:", exc)
    bridge = PetCareBridge(settings, firebase)
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
        print("No se pudo conectar al broker MQTT. Inicia Mosquitto y revisa host/puerto:", exc)
        return 2
    client.loop_start()
    try:
        bridge.run()
    except KeyboardInterrupt:
        print("\nCierre solicitado; no se enviaran mas ordenes.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
