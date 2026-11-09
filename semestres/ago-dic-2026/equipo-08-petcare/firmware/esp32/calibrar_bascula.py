# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: calibrar_bascula.py
# Objetivo: Obtener tara y factor con una masa conocida.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# Ejecuta este archivo una sola vez para obtener TARE_RAW y CALIBRATION_FACTOR.
# El plato debe estar montado en la celda durante toda la calibracion.
from sensores import calibrar_bascula
calibrar_bascula()
