# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: mqtt_config.example.py
# Objetivo: Definir la configuración pública de ejemplo para MQTT de cámara.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: OV2640 integrada; sin conexión TX/RX al DevKit.
# ============================================
# Copiar como mqtt_config.py en la cámara y completar la IP LAN de la PC.
ENABLED = False
HOST = ''
PORT = 1883
USER = ''
PASSWORD = ''
TOPIC = 'petcare/equipo8/cam/frame'
INTERVAL_MS = 700
