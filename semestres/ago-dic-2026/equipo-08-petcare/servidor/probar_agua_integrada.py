# Sistemas Programables - PetCare, Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez. Pines: simulados; no accede a placas.
# Objetivo: HTTP -> MQTT real -> FSM simulada -> registro local -> Firestore real.
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
import requests
import paho.mqtt.client as mqtt
from petcare_server import PetCareBridge, utc_now
from esp32_simulado import ESP32Simulado
from dashboard import start_dashboard
from firestore_rest import FirestoreREST


def run():
    folder=Path(__file__).resolve().parent
    topic='petcare/equipo8/simulacion/agua-'+uuid.uuid4().hex[:10]
    report={'started_at':utc_now(),'simulated':True,'root':topic,'checks':[],
            'scope':'HTTP, MQTT y Firestore reales; sensores, rele y bomba simulados. No mide caudal.'}
    def check(name,value):
        report['checks'].append({'test':name,'passed':bool(value)})
        print(('OK ' if value else 'FALLO ')+name,flush=True)
        if not value:raise AssertionError(name)
    broker=client=sim=server=bridge=None
    stop=threading.Event();worker=None
    with tempfile.TemporaryDirectory() as tmp:
        try:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            conf=Path(tmp)/'broker.conf'
            conf.write_text(f'listener {port} 127.0.0.1\nallow_anonymous true\npersistence false\n')
            broker=subprocess.Popen([shutil.which('mosquitto'),'-c',str(conf)],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            deadline=time.monotonic()+5
            while True:
                try:
                    with socket.create_connection(('127.0.0.1',port),.2):break
                except OSError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.05)
            cfg=json.loads((folder/'server_mqtt_config.json').read_text(encoding='utf-8-sig'))
            db=FirestoreREST(cfg['firebase'],folder)
            bridge=PetCareBridge({'mqtt':{'base_topic':topic},'firebase_root':topic,
                'firebase':{'provider':'firestore'},'water_log_path':str(Path(tmp)/'water.sqlite3')},db)
            client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='agua-test-'+uuid.uuid4().hex[:8])
            ready=threading.Event();client.on_connect=bridge.on_connect;client.on_message=bridge.on_message
            client.on_subscribe=lambda *args:ready.set()
            client.connect('127.0.0.1',port);client.loop_start();bridge.set_mqtt_client(client)
            check('Broker y suscripcion a eventos',ready.wait(5))
            sim=ESP32Simulado(topic);sim.sensors.values['calibrated']=False;sim.sensors.values['weight_g']=None
            sim.connect('127.0.0.1',port)
            def loop():
                while not stop.is_set():sim.tick();time.sleep(.02)
            worker=threading.Thread(target=loop,daemon=True);worker.start()
            deadline=time.monotonic()+10
            while not bridge.dashboard.snapshot()['available']:
                bridge.process_messages()
                if time.monotonic()>deadline:raise TimeoutError('Telemetria')
                time.sleep(.05)
            server=start_dashboard(bridge.dashboard,folder.parent/'interfaz/dashboard.html','127.0.0.1',0)
            url='http://127.0.0.1:'+str(server.server_port)
            state=requests.get(url+'/api/state',timeout=3).json()
            check('Nivel no medido y gramos pendientes',state['telemetry']['status']['water_available'] is None and state['telemetry']['status']['weight_g'] is None)
            headers={'X-PetCare-Token':state['command_token']}
            response=requests.post(url+'/api/command',headers=headers,json={'action':'water','supervised':True},timeout=3)
            check('Boton HTTP acepta servido supervisado',response.status_code==202)
            bridge.process_manual_commands()
            deadline=time.monotonic()+20
            while True:
                bridge.process_messages()
                if bridge.water_log.summary()['total_events']>=2 and bridge.water_log.summary()['pending_cloud']==0:break
                if time.monotonic()>deadline:raise TimeoutError('Eventos en nube')
                time.sleep(.05)
            check('ACK acepta agua manual',any(a.get('action')=='water' and a['ok'] for a in sim.acks))
            check('Bomba simulada termina apagada',not sim.pump.active)
            rows=bridge.water_log.db.execute('SELECT path,payload FROM water ORDER BY rowid').fetchall()
            start,end=[json.loads(row[1]) for row in rows]
            check('Inicio y fin correlacionados',start['run_id']==end['run_id'] and end['phase']=='finished')
            check('Plazo simulado cercano a tres segundos',3000<=end['duration_ms']<3400)
            for path,payload in rows:
                payload=json.loads(payload)
                saved=db.get(path)
                check('Firestore devuelve '+payload['phase'],saved['id']==payload['id'] and saved['volume_ml'] is None and saved['simulated'])
            check('Eventos persistidos sin duplicados',bridge.water_log.summary()=={'total_events':2,'pending_cloud':0})
            report['passed']=True
        finally:
            stop.set()
            if worker:worker.join(2)
            if sim:sim.close()
            if server:server.shutdown();server.server_close()
            if client:client.disconnect();client.loop_stop()
            if bridge:bridge.water_log.close()
            if broker:broker.terminate();broker.wait(5)
            report['finished_at']=utc_now()
            (folder.parent/'docs/PRUEBA_AGUA_INTEGRADA_2026-11-11.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':run()
