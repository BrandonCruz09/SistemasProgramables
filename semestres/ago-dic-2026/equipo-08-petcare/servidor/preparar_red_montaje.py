# Sistemas Programables | PetCare | Equipo 08
# Prepara las copias locales antes de cargarlas a cada placa. No mueve actuadores.
import argparse
import ast
import ipaddress
import json
import re
import subprocess
from pathlib import Path


def asignar(path, values):
    text = path.read_text(encoding='utf-8-sig')
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    edits = []
    remaining = dict(values)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            key = node.targets[0].id
            if key in values:
                edits.append((node.lineno-1,node.end_lineno,key+' = '+repr(values[key])+'\n'))
                remaining.pop(key,None)
    for start,end,new in reversed(edits): lines[start:end] = [new]
    text = ''.join(lines).rstrip()+'\n'
    text += ''.join(k+' = '+repr(v)+'\n' for k,v in remaining.items())
    ast.parse(text)
    path.write_text(text,encoding='utf-8')


def preparar(package):
    profile = json.loads((package/'red_local.json').read_text(encoding='utf-8'))
    result = subprocess.check_output(['netsh','wlan','show','interfaces'],encoding='oem',errors='replace')
    ssid = re.search(r'^\s*SSID\s*:\s*(.+)$',result,re.M)
    if not ssid or ssid.group(1).strip() != profile['ssid']:
        raise SystemExit('Conecta primero la PC a '+profile['ssid']+'. No se cambiaron los archivos.')
    command = "Get-NetIPAddress -InterfaceAlias 'Wi-Fi' -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '169.254.*'} | Select-Object -First 1 -ExpandProperty IPAddress"
    ip = subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True).strip()
    address = ipaddress.IPv4Address(ip)
    if not address.is_private: raise ValueError('Se requiere la IPv4 de la red local')
    folder = Path(__file__).resolve().parent
    cfg = folder/'server_mqtt_config.json'
    settings = json.loads(cfg.read_text(encoding='utf-8-sig'))
    settings['hardware_broker_host'] = ip
    cfg.write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    asignar(package/'01_ESP32/config_local.py',{'MQTT_HOST':ip})
    asignar(package/'02_ESP32CAM/mqtt_config.py',{'HOST':ip})
    for filename,port in [('ABRIR_PANEL.url',8766),('ABRIR_CAMARA.url',8765)]:
        (package/filename).write_text('[InternetShortcut]\nURL=http://%s:%d/\n'%(ip,port),encoding='utf-8')
    (package/'IP_ACTUAL.txt').write_text(ip+'\n',encoding='utf-8')
    print('Archivos preparados. IP de esta PC:',ip)
    print('Panel y camara: http://%s:8766/'%ip)
    print('Carga ahora 01_ESP32 en la placa normal y 02_ESP32CAM en la camara.')
    print('Si cambia esta IP, vuelve a preparar y cargar los dos archivos de configuracion.')
    return ip


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('package',type=Path)
    preparar(parser.parse_args().package)
