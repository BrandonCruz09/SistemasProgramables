# Sistemas Programables | PetCare | Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez.
# Objetivo: comprobar MQTT, panel y Firestore con una captura fisica de la pesa.
# Pines de origen: HX711 DT19/SCK18. Esta prueba PC no envia ordenes a actuadores.
import argparse
import json
import math
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
import requests
import paho.mqtt.client as mqtt
from firestore_rest import FirestoreREST
from petcare_server import PetCareBridge, utc_now
from dashboard import start_dashboard


def run(capture_path, report_path):
    folder = Path(__file__).resolve().parent
    capture = json.loads(Path(capture_path).read_text(encoding='utf-8-sig'))
    payload = capture['payload']
    status = payload['status']
    if payload.get('source') != 'esp32_usb_sensorhub' or not status.get('hx_ok'):
        raise ValueError('Se requiere captura real con HX711 disponible')
    if not math.isfinite(status['weight_g']) or not status.get('calibrated'):
        raise ValueError('Peso no calibrado')
    root = 'petcare/equipo8/pruebas/pesa-' + uuid.uuid4().hex[:10]
    report = {'started_at': utc_now(), 'root': root, 'checks': [], 'passed': False,
              'scope': 'SensorHub real en ESP32 -> USB -> PC -> MQTT real -> puente -> Firestore real. No prueba Wi-Fi de la placa ni activa salidas.',
              'capture': capture}
    def check(name, value):
        report['checks'].append({'test': name, 'passed': bool(value)})
        print(('OK ' if value else 'FALLO ') + name, flush=True)
        if not value:
            raise AssertionError(name)
    broker = client = server = bridge = None
    with tempfile.TemporaryDirectory(prefix='petcare-pesa-') as tmp:
        try:
            settings = json.loads((folder/'server_mqtt_config.json').read_text(encoding='utf-8-sig'))
            db = FirestoreREST(settings['firebase'], folder)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            conf = Path(tmp)/'broker.conf'
            conf.write_text('listener %d 127.0.0.1\nallow_anonymous true\npersistence false\n' % port)
            broker = subprocess.Popen([settings['mosquitto_exe'], '-c', str(conf)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            deadline = time.monotonic()+5
            while True:
                try:
                    with socket.create_connection(('127.0.0.1', port), .2):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError('Broker no disponible')
                    time.sleep(.05)
            bridge = PetCareBridge({'mqtt': {'base_topic': root}, 'firebase_root': root,
                'firebase': {'provider': 'firestore'},
                'water_log_path': str(Path(tmp)/'water.sqlite3')}, db)
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='pesa-'+uuid.uuid4().hex[:8])
            ready = threading.Event()
            client.on_connect = bridge.on_connect
            client.on_message = bridge.on_message
            client.on_subscribe = lambda *args: ready.set()
            client.connect('127.0.0.1', port)
            client.loop_start()
            bridge.set_mqtt_client(client)
            check('Suscripcion MQTT lista', ready.wait(5))
            client.publish(root+'/telemetry', json.dumps(payload), qos=1, retain=False).wait_for_publish(5)
            deadline = time.monotonic()+5
            while bridge.messages.empty():
                if time.monotonic() > deadline:
                    raise TimeoutError('No llego la telemetria')
                time.sleep(.05)
            bridge.process_messages()
            saved = db.get(root+'/latest')
            check('Firestore conserva peso numerico medido',
                  saved is not None and saved['status']['weight_g'] == status['weight_g'])
            for field in ('raw', 'hx_ok', 'calibrated', 'weight_unit', 'calibration_approximate',
                          'calibration_reference_g', 'temperature_c', 'humidity_pct', 'dht_ok',
                          'pir', 'water_available', 'water_level_monitored'):
                check('Campo '+field+' sin alteracion', saved['status'].get(field) == status.get(field))
            check('Origen real y recorrido USB declarados',
                  saved['simulated'] is False and saved['transport_to_pc'] == 'USB_serial')
            check('Timestamp de recepcion guardado', bool(saved.get('received_at')))
            current = db.get(root+'/estado_actual')
            check('Estado actual contiene la misma telemetria', current['telemetria'] == saved)
            history = db.recent(root+'/lecturas')
            check('Historial conserva captura', any(row == saved for row in history.values()))
            response = requests.get(db.base+'/'+db.document_path(root+'/latest'), timeout=8)
            check('Lectura sin autenticacion bloqueada', response.status_code in (401, 403))
            response = requests.patch(db.base+'/'+db.document_path(root+'/probe'), json={'fields': {}}, timeout=8)
            check('Escritura sin autenticacion bloqueada', response.status_code in (401, 403))
            server = start_dashboard(bridge.dashboard, folder.parent/'interfaz/dashboard.html', '127.0.0.1', 0)
            panel = requests.get('http://127.0.0.1:%d/api/state' % server.server_port, timeout=5).json()
            check('Panel HTTP muestra el mismo peso', panel['telemetry']['status']['weight_g'] == status['weight_g'])
            check('Sin ordenes de actuadores', bridge.pending_ia == {} and bridge.dashboard.commands.empty())
            report['stored'] = saved
            report['firestore_document'] = db.document_path(root+'/latest')
            report['passed'] = True
        finally:
            if server:
                server.shutdown(); server.server_close()
            if client:
                client.disconnect(); client.loop_stop()
            if bridge:
                bridge.water_log.db.close()
            if broker:
                broker.terminate()
                try: broker.wait(5)
                except subprocess.TimeoutExpired: broker.kill(); broker.wait(3)
            report['finished_at'] = utc_now()
            Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('capture')
    parser.add_argument('report')
    args = parser.parse_args()
    run(args.capture, args.report)
