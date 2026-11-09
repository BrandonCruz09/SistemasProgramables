# Proyecto: PetCare — Equipo 08 | Sistemas Programables
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293),
# Isaac Eliseo Flores Valencia (22240324), Lidia Verenice Padilla López (22240312).
# Objetivo: guardar resultados en Cloud Firestore desde la PC.
# Pines: no aplica. La autenticación permanece en la PC.
import json
import math
import re
import time
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4
from zoneinfo import ZoneInfo


def encode(value):
    if value is None: return {'nullValue': None}
    if isinstance(value, bool): return {'booleanValue': value}
    if isinstance(value, int): return {'integerValue': str(value)}
    if isinstance(value, float):
        if not math.isfinite(value): raise ValueError('Dato numérico no finito')
        return {'doubleValue': value}
    if isinstance(value, str): return {'stringValue': value}
    if isinstance(value, dict):
        return {'mapValue': {'fields': {k: encode(v) for k, v in value.items()}}}
    if isinstance(value, list): return {'arrayValue': {'values': [encode(v) for v in value]}}
    raise TypeError('Tipo no admitido por el registro de PetCare')


def decode(value):
    if 'nullValue' in value: return None
    if 'integerValue' in value: return int(value['integerValue'])
    if 'doubleValue' in value: return float(value['doubleValue'])
    if 'booleanValue' in value: return value['booleanValue']
    if 'stringValue' in value: return value['stringValue']
    if 'mapValue' in value: return {k: decode(v) for k,v in value['mapValue'].get('fields',{}).items()}
    if 'arrayValue' in value: return [decode(v) for v in value['arrayValue'].get('values',[])]
    raise ValueError('Tipo Firestore no admitido')


class DailyBudget:
    """Tope local persistente; Spark sigue siendo la protección contra cobros.

    Reserva antes de pedir datos. No cuenta operaciones de otras aplicaciones.
    Un único puente por carpeta; el contador se conserva al reiniciar.
    """
    def __init__(self, folder):
        self.path = Path(folder)/'.firestore_budget.json'
        self.lock = threading.Lock()

    def reserve(self, kind, amount=1):
        with self.lock:
            day = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
            data = json.loads(self.path.read_text()) if self.path.exists() else {}
            if data.get('day') != day: data = {'day': day, 'read': 0, 'write': 0}
            limit = {'read': 20000, 'write': 10000}[kind]
            if data[kind] + amount > limit:
                raise RuntimeError('Tope diario local Firestore alcanzado; MQTT sigue local')
            data[kind] += amount
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(data), encoding='utf-8')
            tmp.replace(self.path)


class FirestoreREST:
    """API REST con ID token de Firebase Auth, sometida a las reglas publicadas."""
    provider = 'firestore'
    singletons = {'latest', 'vision', 'command', 'estado_actual', 'probe'}

    def __init__(self, settings, folder, auth=None):
        project = settings.get('project_id', '')
        if not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]', project):
            raise ValueError('Falta project_id válido para Cloud Firestore')
        if auth is None:
            from petcare_server import FirebaseREST
            auth = FirebaseREST(settings, folder)
        self.auth = auth
        self.session = auth.session
        self.base = 'https://firestore.googleapis.com/v1/projects/'+project+'/databases/(default)/documents'
        self.budget = DailyBudget(folder)
        self.blocked_until = 0

    def document_path(self, path):
        parts = path.strip('/').split('/')
        if any(not re.fullmatch(r'[A-Za-z0-9_-]+', p) for p in parts):
            raise ValueError('Ruta Firestore inválida')
        if len(parts) % 2:
            if parts[-1] not in self.singletons: raise ValueError('Se esperaba documento')
            parts.insert(-1, 'estado')
        return '/'.join(parts)

    def _request(self, method, path, body=None, params=None, reads=1):
        if time.monotonic() < self.blocked_until:
            raise RuntimeError('Firestore en espera después de un error de red o cuota')
        self.auth._ensure_token()
        kind = 'read' if method == 'GET' else 'write'
        for attempt in range(2):
            self.budget.reserve(kind, reads if kind == 'read' else 1)
            try:
                response = self.session.request(method, self.base+'/'+quote(path, safe='/'),
                    headers={'Authorization':'Bearer '+self.auth.id_token},
                    json=body, params=params, timeout=8)
            except Exception:
                self.blocked_until = time.monotonic()+60
                raise RuntimeError('Firestore sin conexión; reintento en 60 segundos') from None
            if response.status_code == 401 and attempt == 0:
                self.auth._ensure_token(force=True)
                continue
            if response.status_code == 404 and method == 'GET':
                # Una base inexistente no debe confundirse con un documento vacío.
                message = response.json().get('error',{}).get('message','')
                if message.startswith('Document ') and message.endswith('not found.'): return None
            if not response.ok:
                if response.status_code == 429 or response.status_code >= 500:
                    self.blocked_until = time.monotonic()+60
                raise RuntimeError('Firestore HTTP %s; revisar base, reglas o cuota' % response.status_code)
            return response.json() if response.content else None

    def get(self, path):
        data = self._request('GET', self.document_path(path))
        return None if data is None else {k:decode(v) for k,v in data.get('fields',{}).items()}

    def put(self, path, payload):
        fields = encode(payload)['mapValue']['fields']
        self._request('PATCH', self.document_path(path), {'fields':fields})
        return payload

    def patch(self, path, payload):
        if not payload: return payload
        # Máscara de campos: conserva los demás campos del documento, sin GET extra.
        params = [('updateMask.fieldPaths', '`'+k.replace('\\','\\\\').replace('`','\\`')+'`') for k in payload]
        self._request('PATCH', self.document_path(path),
                      {'fields':encode(payload)['mapValue']['fields']}, params)
        return payload

    def post(self, path, payload):
        key = str(time.time_ns())+'-'+uuid4().hex[:6]
        self.put(path+'/'+key, payload)
        return {'name': key}

    def recent(self, path):
        parts = path.strip('/').split('/')
        if len(parts)%2 != 1 or any(not re.fullmatch(r'[A-Za-z0-9_-]+',p) for p in parts):
            raise ValueError('Se esperaba colección')
        data = self._request('GET', '/'.join(parts), params={'pageSize':120,'orderBy':'received_at desc'}, reads=120)
        return {d['name'].rsplit('/',1)[1]: {k:decode(v) for k,v in d.get('fields',{}).items()}
                for d in (data or {}).get('documents',[])}
