# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: banco_pesa.py
# Objetivo: Leer RAW y convertir a gramos solamente con calibración válida.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: HX711 DT19/SCK18; DHT22 DATA4; PIR OUT27; servo33; bomba23.
# ============================================
import json
import math
import os
import time
from hx711 import HX711

CAL_FILE = 'calibracion_pesa.json'


def numero_finito(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def validar_calibracion(data):
    if not isinstance(data, dict):
        raise ValueError('Calibracion invalida')
    if not numero_finito(data.get('tara')):
        raise ValueError('Tara invalida')
    factor = data.get('factor')
    if not numero_finito(factor) or factor == 0:
        raise ValueError('Factor invalido')
    mass = data.get('masa_referencia_g')
    if not numero_finito(mass) or mass <= 0:
        raise ValueError('Masa de referencia invalida')
    return data


def calcular(tara, cargada, masa, ruido):
    if not numero_finito(masa) or masa <= 0:
        raise ValueError('Escribe una masa real, positiva, en gramos')
    delta = cargada - tara
    # Exigir un cambio mayor que el ruido observado al tomar las muestras.
    if abs(delta) <= max(50, 5 * ruido):
        raise ValueError('El cambio es pequeno o inestable. Revisa montaje y repite.')
    return validar_calibracion({'tara': tara, 'factor': delta / masa,
                               'masa_referencia_g': masa})


class Pesa:
    def __init__(self):
        self.hx = HX711(19, 18)
        self.cal = None
        try:
            with open(CAL_FILE) as f:
                self.cal = validar_calibracion(json.load(f))
        except (OSError, ValueError, TypeError):
            pass

    def muestra(self, cantidad=5):
        values = [self.hx.read_raw(timeout_ms=1000) for _ in range(cantidad)]
        if any(abs(value) >= 8388000 for value in values):
            raise ValueError('HX711 saturado: revisar celda y cableado')
        return sum(values) / len(values), max(values) - min(values)

    def gramos(self):
        if self.cal is None:
            raise ValueError('PENDIENTE: primero usa la opcion 1 para calibrar')
        raw, _ = self.muestra(5)
        # Promedio de cinco conversiones. Se conserva el signo para no ocultar errores.
        return (raw - self.cal['tara']) / self.cal['factor']

    def guardar(self, data):
        validar_calibracion(data)
        temp = CAL_FILE + '.tmp'
        with open(temp, 'w') as f:
            json.dump(data, f)
        with open(temp) as f:
            validar_calibracion(json.load(f))
        os.rename(temp, CAL_FILE)
        self.cal = data

    def calibrar(self):
        print('Plato instalado en su soporte; respeta la capacidad de la celda.')
        print('Usa una masa medida. Una botella de 1.5 L NO equivale a 1500 g totales.')
        entry = input('Masa conocida en GRAMOS (Enter cancela): ').strip()
        if not entry:
            return
        masa = float(entry.replace(',', '.'))
        if not numero_finito(masa) or masa <= 0:
            raise ValueError('Masa invalida')
        input('Deja SOLO el plato vacio, sin tocarlo. Enter para tomar la tara: ')
        time.sleep_ms(1500)
        tara, ruido_vacio = self.muestra(20)
        print('Tara tomada.')
        input('Coloca la masa conocida y no toques el soporte. Enter para medir: ')
        time.sleep_ms(1500)
        loaded, ruido_carga = self.muestra(20)
        data = calcular(tara, loaded, masa, max(ruido_vacio, ruido_carga))
        self.guardar(data)
        print('Calibracion guardada en la ESP32. Ya se mostraran gramos.')
        print('TARE_RAW =', data['tara'])
        print('CALIBRATION_FACTOR =', data['factor'])
        print('Retira y vuelve a colocar la masa para comprobar; prueba otra masa tambien.')

    def tarar(self):
        if self.cal is None:
            raise ValueError('Primero calibra con la opcion 1')
        input('Deja el plato vacio y no lo toques. Enter: ')
        time.sleep_ms(1500)
        tara, _ = self.muestra(20)
        data = dict(self.cal)
        data['tara'] = tara
        self.guardar(data)
        print('Cero actualizado sin cambiar el factor.')
