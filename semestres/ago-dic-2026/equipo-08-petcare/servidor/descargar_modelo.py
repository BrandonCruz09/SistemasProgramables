# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: descargar_modelo.py
# Objetivo: Descargar el modelo original y comprobar su integridad.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; ejecutado en PC.
# ============================================
import hashlib
import json
from pathlib import Path
import requests


def main():
    folder = Path(__file__).resolve().parent / 'models'
    records = json.loads((folder / 'manifest.json').read_text(encoding='utf8'))
    for record in records:
        dest = folder / record['file']
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == record['sha256']:
            print('Comprobado:', dest.name)
            continue
        response = requests.get(record['url'], timeout=(5, 60))
        response.raise_for_status()
        data = response.content
        if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError('Descarga incompleta o distinta: ' + dest.name)
        temporary = dest.with_suffix(dest.suffix + '.part')
        temporary.write_bytes(data)
        temporary.replace(dest)
        print('Descargado y comprobado:', dest.name)


if __name__ == '__main__':
    main()
