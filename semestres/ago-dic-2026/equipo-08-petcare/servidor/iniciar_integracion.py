# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: iniciar_integracion.py
# Objetivo: Iniciar y detener broker, visión y puente en la PC.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; software en PC.
# ============================================
"""Un proceso visible coordina broker y servicios; Ctrl+C cierra los hijos."""
import json
import socket
import subprocess
import sys
import time
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true',help='Comprobar inicio local y cerrar sin esperar hardware')
    args=parser.parse_args()
    folder=Path(__file__).resolve().parent
    cfg=folder/'server_mqtt_config.json'
    if not cfg.exists() or not (folder/'broker.local.conf').exists():
        raise SystemExit('Falta el perfil MQTT privado. Consultar la guía de integración.')
    settings=json.loads(cfg.read_text(encoding='utf-8'))
    port=int(settings['mqtt'].get('port',1883))
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',port)) == 0:
            raise SystemExit('El puerto MQTT ya está ocupado. Cierra la sesión anterior; no se detuvo ningún proceso ajeno.')
    processes=[];logs=[]
    try:
        commands=[('broker',[settings['mosquitto_exe'],'-c',str(folder/'broker.local.conf')]),
                  ('vision_mqtt',[sys.executable,str(folder/'vision_main.py'),'--config',str(cfg)]),
                  ('bridge_mqtt',[sys.executable,str(folder/'mqtt_bridge.py'),'--config',str(cfg)])]
        for name,cmd in commands:
            log=open(folder/(name+'.log'),'w',encoding='utf-8');logs.append(log)
            process=subprocess.Popen(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            processes.append(process)
            time.sleep(.5)
            if process.poll() is not None:
                raise RuntimeError('No inició '+name+'. Revisar '+name+'.log')
        print('PETCARE — integración MQTT e IA',flush=True)
        print('Celular: http://%s:%s/' % (settings['hardware_broker_host'],settings.get('web',{}).get('port',8765)),flush=True)
        print('Dashboard: http://%s:%s/' % (settings['hardware_broker_host'],settings.get('dashboard',{}).get('port',8766)),flush=True)
        print('Conecta ambas placas al mismo Wi-Fi. La señal IA usa RGB blanco 1.5 s.',flush=True)
        cloud = settings.get('firebase', {})
        print('Nube: '+(cloud.get('provider','rtdb') if cloud.get('enabled') else 'desactivada')+
              '. Ctrl+C cierra los servicios.',flush=True)
        if args.check:
            import urllib.request
            for port,path in ((8765,'/api/status'),(8766,'/api/state')):
                deadline=time.monotonic()+8
                while True:
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:%d%s'%(port,path),timeout=1) as response:
                            data=json.load(response)
                        print('HTTP',port,'responde; datos físicos disponibles:',data.get('available'),flush=True)
                        break
                    except OSError:
                        if time.monotonic()>deadline:raise
                        time.sleep(.2)
            return
        while all(p.poll() is None for p in processes):time.sleep(.3)
        print('Un servicio terminó; consultar broker.log, vision_mqtt.log y bridge_mqtt.log.')
    except KeyboardInterrupt:
        print('Cierre solicitado.')
    finally:
        for process in reversed(processes):
            if process.poll() is None:process.terminate()
        for process in reversed(processes):
            try:process.wait(5)
            except subprocess.TimeoutExpired:process.kill();process.wait(3)
        for log in logs:log.close()


if __name__=='__main__':main()
