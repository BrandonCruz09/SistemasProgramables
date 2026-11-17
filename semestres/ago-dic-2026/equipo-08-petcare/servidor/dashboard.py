# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: dashboard.py
# Objetivo: Servir estado e histórico de solo lectura sin exponer credenciales.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; software en PC.
# ============================================
"""Panel de solo lectura; las credenciales Firebase permanecen en la PC."""
import copy
import json
import threading
import time
import queue
import secrets
from urllib.parse import urlsplit
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from http_local import LocalHTTPServer


class DashboardState:
    def __init__(self):
        self.lock=threading.Lock()
        self.history=deque(maxlen=120)
        self.events=deque(maxlen=20)
        self.telemetry=None
        self.received=0
        self.vision={}
        self.cloud={'status':'desactivado'}
        self.water_log = {'total_events':0, 'pending_cloud':0}
        self.commands = queue.Queue(maxsize=10)
        self.command_token = secrets.token_hex(16)

    def request_command(self, action, supervised=False):
        if action not in ('feed', 'water', 'stop_water', 'stop_food', 'signal_dog'):
            return False, 'Accion desconocida'
        data = self.snapshot()
        if action not in ('stop_water', 'stop_food'):
            if not data['available'] or data['age_seconds'] > 15:
                return False, 'No hay datos recientes del ESP32'
            if data['telemetry']['status'].get('state') != 'LISTO':
                return False, 'El equipo esta ocupado'
            status = data['telemetry']['status']
            if status.get('actions_allowed') is False:
                return False, 'Modo diagnostico; actuadores bloqueados'
            if action == 'feed' and (status.get('servo_enabled') is not True or not status.get('hx_ok') or not status.get('calibrated') or status.get('food_active')):
                return False, 'Revisa servo y pesa antes de servir alimento'
            if action == 'water' and (status.get('servo_holding_pwm') or status.get('food_active')):
                return False, 'Agua bloqueada mientras se valida la alimentacion del servo'
        if action == 'water' and supervised is not True:
            return False, 'Confirma que hay agua y espacio en el plato'
        try:
            self.commands.put_nowait({'action':action,'supervised':supervised,
                'session_id':(data['telemetry'] or {}).get('status',{}).get('session_id'),
                'queued_at':time.monotonic()})
        except queue.Full:
            return False, 'Espera a que termine la orden anterior'
        return True, 'Orden en cola; espera la confirmacion del ESP32'

    def update(self, payload):
        with self.lock:
            self.telemetry=copy.deepcopy(payload)
            self.history.append(copy.deepcopy(payload))
            self.received=time.monotonic()

    def restore_history(self, history):
        if not isinstance(history,dict):return
        with self.lock:
            for key in sorted(history)[-120:]:
                if isinstance(history[key],dict):self.history.append(history[key])

    def snapshot(self):
        with self.lock:
            age=time.monotonic()-self.received if self.received else None
            return copy.deepcopy({'telemetry':self.telemetry,'history':list(self.history),
                'events':list(self.events),'vision':self.vision,'firebase':self.cloud,
                'water_log':self.water_log, 'command_token':self.command_token,
                'age_seconds':round(age,1) if age is not None else None,
                'available':age is not None and age<30})


def start_dashboard(state, html_path, host='0.0.0.0', port=8766, demo_mode=False):
    html=Path(html_path).read_bytes()
    if demo_mode:
        html=html.replace(b'data-demo="false"', b'data-demo="true"')
    assets=Path(html_path).resolve().parent/'assets'
    public_assets={'dashboard.css':'text/css; charset=utf-8',
                   'dashboard.js':'application/javascript; charset=utf-8',
                   'petcare-dog.webp':'image/webp'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            self.connection.settimeout(2)
            if self.path != '/api/command':
                self.send_error(404);return
            origin = self.headers.get('Origin')
            if origin and urlsplit(origin).netloc != self.headers.get('Host'):
                self.send_error(403);return
            if self.headers.get('X-PetCare-Token') != state.command_token:
                self.send_error(403);return
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 1024: raise ValueError()
                data = json.loads(self.rfile.read(length))
                if not isinstance(data,dict): raise ValueError()
                ok,message = state.request_command(data.get('action'),data.get('supervised'))
            except (ValueError, OSError):
                self.send_error(400);return
            body=json.dumps({'ok':ok,'message':message}).encode()
            self.send_response(202 if ok else 409)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            path=self.path.split('?')[0]
            if path=='/':body,mime=html,'text/html; charset=utf-8'
            elif path=='/api/state':body,mime=json.dumps(state.snapshot(),allow_nan=False).encode(),'application/json'
            elif path.startswith('/assets/') and path[8:] in public_assets:
                name=path[8:]
                try: body=(assets/name).read_bytes()
                except OSError: self.send_error(404);return
                mime=public_assets[name]
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',mime)
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
    server=LocalHTTPServer((host,int(port)),Handler)
    server.daemon_threads=True
    threading.Thread(target=server.serve_forever,daemon=True,name='dashboard').start()
    return server
