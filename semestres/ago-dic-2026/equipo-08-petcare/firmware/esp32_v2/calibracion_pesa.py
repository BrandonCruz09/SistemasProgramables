"""Lectura de la referencia conservada. Este modulo nunca escribe archivos."""
# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Cargar y validar la calibración guardada de la celda de carga.

import json
import math


def cargar(folder=""):
    ruta = (folder.rstrip("/") + "/" if folder else "") + "calibracion_validada.json"
    try:
        with open(ruta) as archivo:
            datos = json.load(archivo)
        factor, tara = datos["CALIBRATION_FACTOR"], datos["TARE_RAW"]
        for n in (factor, tara):
            if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n):
                raise ValueError("Numero de calibracion invalido")
        if factor == 0 or abs(tara) >= 8388607:
            raise ValueError("Factor o tara fuera de rango")
        return {
            "factor": factor,
            "tara": tara,
            "error": None,
            "aproximada": datos.get("referencia_aproximada", True),
            "referencia_g": datos.get("masa_referencia_g"),
            "archivo": ruta,
        }
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {
            "factor": None,
            "tara": None,
            "error": repr(error),
            "aproximada": True,
            "referencia_g": None,
            "archivo": ruta,
        }
