# Sistemas Programables | PetCare | Equipo 08
# Prueba local con imagen y telemetria sinteticas; no conecta placas ni Firestore.
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import cv2
import numpy as np
import paho.mqtt.client as mqtt
import requests


def run():
    folder=Path(__file__).resolve().parent
    private=json.loads((folder/'server_mqtt_config.json').read_text(encoding='utf-8-sig'))
    report={'simulated':True,'actuators_used':False,'firestore_used':False,'checks':[]}
    processes=[]; handles=[]; client=None
    def check(name, condition):
        report['checks'].append({'test':name,'passed':bool(condition)})
        if not condition: raise AssertionError(name)
        print('OK',name,flush=True)
    with tempfile.TemporaryDirectory(prefix='petcare-web-') as tmp:
        tmp=Path(tmp)
        try:
            with socket.socket() as s:
                s.bind(('127.0.0.1',0)); mqtt_port=s.getsockname()[1]
            topic='petcare/equipo8/simulacion/preparacion15nov'
            conf=tmp/'broker.conf'
            conf.write_text('listener %d 127.0.0.1\nallow_anonymous true\npersistence false\n'%mqtt_port)
            settings={'mqtt':{'host':'127.0.0.1','port':mqtt_port,'base_topic':topic,'frame_topic':topic+'/cam/frame'},
                'camera_transport':'mqtt','vision':private.get('vision',{}),
                'vision_url':'http://127.0.0.1:8765/api/status','camera_stream_url':'',
                'firebase':{'enabled':False},'firebase_root':topic,
                'water_log_path':str(tmp/'water.sqlite3'),
                'web':{'host':'127.0.0.1','port':8765},
                'dashboard':{'enabled':True,'host':'127.0.0.1','port':8766}}
            cfg=tmp/'test.json';cfg.write_text(json.dumps(settings),encoding='utf-8')
            commands=[[private['mosquitto_exe'],'-c',str(conf)],
                [sys.executable,str(folder/'vision_main.py'),'--config',str(cfg)],
                [sys.executable,str(folder/'mqtt_bridge.py'),'--config',str(cfg)]]
            for n,cmd in enumerate(commands):
                log=open(tmp/('%d.log'%n),'w',encoding='utf-8');handles.append(log)
                processes.append(subprocess.Popen(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
                time.sleep(.6)
                if processes[-1].poll() is not None: raise RuntimeError('Fallo servicio '+str(n))
            for port,path in [(8765,'/api/status'),(8766,'/api/state')]:
                deadline=time.monotonic()+15
                while True:
                    try: requests.get('http://127.0.0.1:%d%s'%(port,path),timeout=1).raise_for_status();break
                    except requests.RequestException:
                        if time.monotonic()>deadline: raise
                        time.sleep(.3)
                check('Servicio HTTP '+str(port),True)
            client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.connect('127.0.0.1',mqtt_port);client.loop_start()
            frame=np.zeros((240,320,3),dtype=np.uint8)
            cv2.putText(frame,'PRUEBA SIMULADA',(15,120),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
            jpeg=cv2.imencode('.jpg',frame)[1].tobytes()
            available=False
            for _ in range(20):
                client.publish(topic+'/cam/frame',jpeg).wait_for_publish(2)
                time.sleep(.25)
                status=requests.get('http://127.0.0.1:8765/api/status',timeout=2).json()
                if status.get('available'): available=True; break
            check('JPEG por MQTT procesado por el modelo real',available)
            with requests.get('http://127.0.0.1:8765/stream',stream=True,timeout=3) as response:
                check('Video HTTP multipart con JPEG', 'multipart' in response.headers.get('Content-Type','') and b'\xff\xd8' in next(response.iter_content(4096)))
            telemetry={'simulated':True,'status':{'weight_g':163.2,'calibrated':True,'hx_ok':True,'weight_unit':'g','state':'LISTO'}}
            for _ in range(10):
                client.publish(topic+'/telemetry',json.dumps(telemetry)).wait_for_publish(2)
                time.sleep(.2)
                panel=requests.get('http://127.0.0.1:8766/api/state',timeout=2).json()
                if panel.get('telemetry'):break
            check('Panel recibe gramos simulados',panel['telemetry']['status']['weight_g']==163.2)
            check('Pagina contiene video integrado','id="liveVideo"' in requests.get('http://127.0.0.1:8766/',timeout=2).text)
            time.sleep(5)
            check('Camara sin cuadros pasa a no disponible',not requests.get('http://127.0.0.1:8765/api/status',timeout=2).json()['available'])
            report['passed']=True
        finally:
            if client:client.disconnect();client.loop_stop()
            for p in reversed(processes):
                if p.poll() is None:p.terminate()
            for p in processes:
                try:p.wait(5)
                except subprocess.TimeoutExpired:p.kill();p.wait(3)
            for h in handles:h.close()
            (folder.parent/'docs/PRUEBA_PREPARACION_15NOV.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            if not report.get('passed'):
                for log in tmp.glob('*.log'):print(log.read_text(encoding='utf-8',errors='replace')[-1600:])


if __name__=='__main__':run()
