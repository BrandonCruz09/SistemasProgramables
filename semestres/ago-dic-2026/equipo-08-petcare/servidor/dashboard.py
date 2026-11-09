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
                'age_seconds':round(age,1) if age is not None else None,
                'available':age is not None and age<30})


def start_dashboard(state, html_path, host='0.0.0.0', port=8766):
    html=Path(html_path).read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            path=self.path.split('?')[0]
            if path=='/':body,mime=html,'text/html; charset=utf-8'
            elif path=='/api/state':body,mime=json.dumps(state.snapshot(),allow_nan=False).encode(),'application/json'
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
