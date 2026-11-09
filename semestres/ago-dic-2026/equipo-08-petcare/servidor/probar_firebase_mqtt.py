# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: probar_firebase_mqtt.py
# Objetivo: Verificar Firebase real y MQTT local con una ESP32 simulada.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; no abre puertos serie ni controla hardware.
# ============================================
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import paho.mqtt.client as mqtt
import requests
from esp32_simulado import ESP32Simulado
from petcare_server import FirebaseREST, PetCareBridge, utc_now

FOLDER = Path(__file__).resolve().parent


def run():
    settings = json.loads((FOLDER/'firebase_sim_config.json').read_text(encoding='utf-8-sig'))
    firebase = FirebaseREST(settings['firebase'], FOLDER)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
    root = 'petcare/equipo8/simulacion/'+run_id
    topic = root
    checks = []
    report = {'run_id':run_id, 'simulated':True, 'firebase_root':root,
              'started_at':utc_now(), 'checks':checks, 'passed':False}

    def record(name, success, detail):
        checks.append({'test':name, 'passed':bool(success), 'detail':detail})
        print(('OK' if success else 'FALLO')+' | '+name+' | '+detail, flush=True)
        if not success: raise AssertionError(name)

    broker = None
    sim = None
    client = None
    temp = tempfile.TemporaryDirectory(prefix='petcare-mqtt-')
    broker_log = None
    try:
        # Ningun dato de esta prueba corresponde a sensores fisicos.
        sample = {'simulated':True, 'weight_g':75.0, 'created_at':utc_now(), 'run_id':run_id}
        firebase.put(root+'/probe', sample)
        record('Firebase escritura y lectura', firebase.get(root+'/probe') == sample,
               'PUT y GET devolvieron el mismo objeto')
        unauth = requests.get(settings['firebase']['database_url'].rstrip('/')+'/'+root+'/probe.json', timeout=10)
        record('Acceso publico bloqueado', unauth.status_code in (401,403), 'HTTP '+str(unauth.status_code)+' sin token')
        outside = requests.get(settings['firebase']['database_url'].rstrip('/')+'/petcare/equipo8/latest.json',
                               params={'auth':firebase.id_token},timeout=10)
        record('Acceso limitado a simulacion', outside.status_code in (401,403),
               'La identidad de prueba no puede leer datos de hardware')
        uid = firebase.uid
        firebase._ensure_token(force=True)
        record('Renovacion de sesion', firebase.uid == uid and firebase.get(root+'/probe') == sample,
               'La sesion renovada conserva identidad y acceso')

        exe = settings.get('mosquitto_exe') or shutil.which('mosquitto')
        if not exe or not Path(exe).exists(): raise FileNotFoundError('Falta Mosquitto; configura mosquitto_exe')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port = sock.getsockname()[1]
        conf = Path(temp.name)/'mosquitto.conf'
        conf.write_text('listener %s 127.0.0.1\nallow_anonymous true\npersistence false\n' % port)
        broker_log = open(Path(temp.name)/'broker.log','wb')
        broker = subprocess.Popen([exe,'-c',str(conf)], stdout=broker_log, stderr=subprocess.STDOUT,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        deadline = time.monotonic()+5
        while True:
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.2): break
            except OSError:
                if time.monotonic()>deadline or broker.poll() is not None:
                    raise RuntimeError('Mosquitto local no inicio')
                time.sleep(.1)
        report['mqtt']={'host':'127.0.0.1','port':port,'topic':topic}
        bridge = PetCareBridge({'mqtt':{'base_topic':topic}, 'firebase_root':root,
                                'command_interval_seconds':1}, firebase)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='bridge-'+run_id)
        ready = threading.Event()
        client.on_connect = bridge.on_connect
        client.on_message = bridge.on_message
        client.on_subscribe = lambda *args: ready.set()
        bridge.set_mqtt_client(client)
        client.connect('127.0.0.1',port,30)
        client.loop_start()
        if not ready.wait(5): raise TimeoutError('El puente no se suscribio a MQTT')
        sim = ESP32Simulado(topic)
        sim.connect('127.0.0.1',port)

        def pump_until(predicate, timeout=15):
            end = time.monotonic()+timeout
            while time.monotonic()<end:
                sim.tick()
                bridge.process_messages()
                bridge.poll_command()
                if predicate(): return True
                time.sleep(.05)
            return False

        pump_until(lambda: len(checks)<0, timeout=2)
        received = firebase.get(root+'/latest')
        record('Telemetria MQTT a Firebase', isinstance(received,dict) and received.get('simulated') is True
               and received.get('status',{}).get('weight_g')==75.0,
               'ESP32 simulada -> Mosquitto -> puente -> latest; peso 75 g ficticio')
        events = firebase.get(root+'/events')
        record('Historial guardado', isinstance(events,dict) and bool(events), 'Se guardo al menos un evento simulado')

        def command(name, action, expected):
            cid = run_id+'-'+str(len(checks))
            firebase.put(root+'/command', {'id':cid,'action':action,'status':'pendiente',
                                           'simulated':True,'created_at':utc_now()})
            done = pump_until(lambda:any(a['id']==cid for a in sim.acks))
            bridge.process_messages()
            saved = firebase.get(root+'/command')
            wanted = 'aceptado' if expected else 'rechazado'
            record(name, done and saved.get('status')==wanted,
                   'Firebase -> MQTT -> FSM -> ack -> Firebase: '+str(saved.get('status')))
            return cid

        cid = command('Orden de alimento', 'feed', True)
        record('Cierre de compuerta simulada', pump_until(lambda:sim.controller.state=='LISTO'),
               'La FSM vuelve a LISTO y libera el servo simulado')
        angles_before = len(sim.servo.angles)
        ack_before = len(sim.acks)
        client.publish(topic+'/commands',json.dumps({'id':cid,'action':'feed'}),qos=1).wait_for_publish(3)
        duplicated = pump_until(lambda:len(sim.acks)>ack_before)
        record('Comando duplicado', duplicated and not sim.acks[-1]['ok'] and len(sim.servo.angles)==angles_before,
               'No repitio el movimiento simulado')
        sim.sensors.values['weight_g']=300.0
        command('Bloqueo por plato lleno','feed',False)
        sim.sensors.values.update(weight_g=None,calibrated=False)
        command('Bloqueo sin calibracion','feed',False)
        sim.sensors.values.update(weight_g=75.0,calibrated=True,water_available=False)
        command('Bloqueo sin agua','water',False)
        sim.sensors.values['water_available']=True
        command('Orden de agua','water',True)
        record('Tiempo limite de bomba simulada', pump_until(lambda:sim.controller.state=='LISTO') and not sim.pump.active,
               'La salida simulada queda apagada')
        command('Orden de detener agua','stop_water',True)
        firebase.put(root+'/command', {'id':run_id+'-invalid','action':'servo_180','status':'pendiente','simulated':True})
        pump_until(lambda:False,timeout=2)
        record('Orden invalida rechazada', firebase.get(root+'/command').get('status')=='rechazado',
               'El puente rechazo una accion no permitida')
        firebase.put(root+'/vision', {'simulated':True,'available':True,'dog_detected':True,
                                      'person_detected':False,'source':'fixture-software','processed_at':utc_now()})
        record('Estado de vision de demostracion', firebase.get(root+'/vision').get('simulated') is True,
               'Ejemplo ficticio; no es inferencia de la camara')
        bridge.ia_enabled = True
        command_ia = bridge.process_vision({'available':True,'dog_detected':True,
            'frame_age_seconds':.1,'frame_number':1,'processed_at':utc_now(),
            'detections':[{'class':'dog','confidence':.90}],'uncertain_detections':0})
        record('Decision IA de ejemplo enviada', command_ia is not None,
               'Resultado dog inyectado; orden signal_dog, sin alimento ni agua')
        done = pump_until(lambda: any(a['id']==command_ia['id'] for a in sim.acks))
        pump_until(lambda:command_ia['id'] not in bridge.pending_ia, timeout=5)
        event_ia = firebase.get(root+'/eventos_ia/'+command_ia['id'])
        record('Evento IA y ACK guardados en Firebase', done and event_ia.get('estado')=='confirmado',
               'RTDB real; actuador y deteccion simulados, ambos declarados')
        record('Rutas de Sprint 3 con datos simulados', bool(firebase.get(root+'/lecturas')) and
               firebase.get(root+'/estado_actual').get('telemetria',{}).get('simulated') is True,
               'lecturas y estado_actual devueltos por Firebase')
        report['passed']=True
    except Exception as exc:
        # No imprimir URLs de autenticacion ni configuraciones privadas.
        report['error_type']=type(exc).__name__
        print('Prueba interrumpida: '+type(exc).__name__,flush=True)
        raise
    finally:
        if sim: sim.close()
        if client:
            client.disconnect()
            client.loop_stop()
        if broker:
            broker.terminate()
            try: broker.wait(5)
            except subprocess.TimeoutExpired:
                broker.kill()
                broker.wait(5)
        if broker_log: broker_log.close()
        temp.cleanup()
        report['finished_at']=utc_now()
        (FOLDER/'simulacion_resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            firebase.put(root+'/report',report)
        except Exception:
            print('No se pudo guardar el reporte en nube; se conserva localmente.',flush=True)
    print('COMPLETADO | '+root,flush=True)
    return report


if __name__=='__main__':
    run()
