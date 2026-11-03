# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: main.py
# Objetivo: Iniciar la camara al conectar la alimentacion.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: OV2640 integrada; USB de ESP32CAM-MB.
# ============================================
import time

try:
    print('PetCare inicia en 3 segundos. Ctrl+C cancela el arranque.')
    time.sleep(3)
    from camara_wifi import main
    main()
except KeyboardInterrupt:
    print('Arranque cancelado.')
