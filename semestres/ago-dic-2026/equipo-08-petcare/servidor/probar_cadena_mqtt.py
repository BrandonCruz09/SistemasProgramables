# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: probar_cadena_mqtt.py
# Objetivo: Verificar transporte JPEG y respuesta con dispositivos simulados.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; software en PC.
# ============================================
"""Broker real; cámara, resultado de IA y actuador simulados y declarados."""
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import Mock
import cv2
import numpy as np
import paho.mqtt.client as mqtt
from mqtt_camera import MQTTCameraStream
from petcare_server import PetCareBridge, utc_now
from esp32_simulado import ESP32Simulado
from detector import DogPersonDetector


def run():
    folder=Path(__file__).resolve().parent
    topic='petcare/equipo8/simulacion/cadena-'+uuid.uuid4().hex[:8]
    report={'simulated':True,'started_at':utc_now(),'checks':[],
            'scope':'Broker real y JPEG sintético. Detección dog inyectada para probar decisiones; no es precisión de IA.'}
    def check(name,value):
        report['checks'].append({'test':name,'passed':bool(value)})
        print(('OK ' if value else 'FALLO ')+name,flush=True)
        if not value:raise AssertionError(name)
    broker=None;client=None;cam=None;sim=None
    with tempfile.TemporaryDirectory(prefix='petcare-cadena-') as tmp:
        try:
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            conf=Path(tmp)/'broker.conf';conf.write_text(f'listener {port} 127.0.0.1\nallow_anonymous true\npersistence false\n')
            broker=subprocess.Popen([shutil.which('mosquitto'),'-c',str(conf)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            deadline=time.monotonic()+5
            while True:
                try:
                    with socket.create_connection(('127.0.0.1',port),.2):break
                except OSError:
                    if time.monotonic()>deadline:raise TimeoutError('Broker')
                    time.sleep(.05)
            settings={'host':'127.0.0.1','port':port,'base_topic':topic,'frame_topic':topic+'/cam/frame'}
            cam=MQTTCameraStream(settings);cam.start()
            check('Suscripción PC al tópico de frames',cam.ready.wait(5))
            db=Mock();bridge=PetCareBridge({'mqtt':settings,'firebase_root':topic,
                 'automation':{'dog_indicator_enabled':True}},db)
            client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='test-'+uuid.uuid4().hex[:8])
            ready=threading.Event();client.on_connect=bridge.on_connect;client.on_message=bridge.on_message
            client.on_subscribe=lambda *args:ready.set()
            client.connect('127.0.0.1',port);client.loop_start();bridge.set_mqtt_client(client)
            check('Suscripción puente a telemetría y ACK',ready.wait(5))
            sim=ESP32Simulado(topic);sim.connect('127.0.0.1',port)
            image=np.zeros((240,320,3),np.uint8)
            cv2.putText(image,'SIMULACION',(20,120),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
            jpeg=cv2.imencode('.jpg',image)[1].tobytes()
            client.publish(cam.topic,jpeg,qos=0,retain=False).wait_for_publish(3)
            number,received,stamp,error=cam.latest(timeout=3)
            check('JPEG atraviesa MQTT sin alteración',received==jpeg and error is None)
            decoded=cv2.imdecode(np.frombuffer(received,np.uint8),cv2.IMREAD_COLOR)
            check('OpenCV decodifica el frame recibido',decoded is not None and decoded.shape[:2]==(240,320))
            # Ejecutar además el modelo real sobre este cuadro; no es un perro real.
            detector=DogPersonDetector(folder/'models')
            annotated,result=detector.analyze(decoded)
            check('Modelo real ejecuta inferencia en PC',annotated.shape==decoded.shape and result['available'])
            fixture={'available':True,'dog_detected':True,'frame_age_seconds':.1,
                     'frame_number':number,'processed_at':utc_now(),'detections':[{'class':'dog','confidence':.9}],
                     'uncertain_detections':0,'simulated':True}
            command=bridge.process_vision(fixture)
            check('Decisión de ejemplo publica signal_dog',command and command['action']=='signal_dog')
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                sim.tick();bridge.process_messages()
                if command['id'] not in bridge.pending_ia:break
                time.sleep(.02)
            check('ESP32 simulada recibe y confirma',any(a['id']==command['id'] and a['ok'] for a in sim.acks))
            check('RGB simulado enciende blanco',sim.led.color=='white')
            check('IA no activa servo ni bomba',not sim.servo.angles and not sim.pump.active)
            check('Puente correlaciona el ACK',command['id'] not in bridge.pending_ia)
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:sim.tick();time.sleep(.02)
            check('Señal termina sin otra orden',sim.led.color!='white')
            fixture['frame_number']+=1
            check('No repite con el perro presente',bridge.process_vision(fixture) is None)
            report['passed']=True
        finally:
            if sim:sim.close()
            if cam:cam.stop()
            if client:client.disconnect();client.loop_stop()
            if broker:
                broker.terminate()
                try:broker.wait(4)
                except subprocess.TimeoutExpired:broker.kill();broker.wait(3)
            report['finished_at']=utc_now()
            (folder.parent/'docs/PRUEBA_CADENA_MQTT_2026-11-08.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':run()
