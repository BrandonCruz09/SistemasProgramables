# Sistemas Programables | PetCare | Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez.
# Objetivo: recuperar y validar la calibracion persistente del plato.
# Pines asociados: HX711 DT19, SCK18, VCC3V3 y GND.
import json
import math


def numero(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Se esperaba un numero')
    if not math.isfinite(value):
        raise ValueError('Numero no finito')
    return value


def cargar(folder=''):
    """La tara mas reciente tiene prioridad; un archivo invalido bloquea los gramos."""
    prefix = folder.rstrip('/') + '/' if folder else ''
    try:
        with open(prefix + 'calibracion_pesa_prueba.json') as archivo:
            datos = json.load(archivo)
        factor = numero(datos['CALIBRATION_FACTOR'])
        if factor == 0:
            raise ValueError('Factor cero')
        tara = numero(datos['TARE_RAW'])
        try:
            with open(prefix + 'tara_tazon.json') as archivo:
                ultima = json.load(archivo)
        except OSError as error:
            if error.args[0] != 2:
                raise
        else:
            tara = numero(ultima['TARE_RAW'])
        if abs(tara) >= 8388607:
            raise ValueError('Tara fuera del rango HX711')
        referencia = datos.get('masa_referencia_g')
        if referencia is not None and numero(referencia) <= 0:
            raise ValueError('Referencia no positiva')
        return {'tara': tara, 'factor': factor,
                'aproximada': datos.get('referencia_aproximada', True) is not False,
                'referencia_g': referencia, 'error': None}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {'tara': None, 'factor': None, 'aproximada': True,
                'referencia_g': None, 'error': str(error)}
