# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: probar_camara.py
# Objetivo: Comprobar tres capturas JPEG sin Wi-Fi y liberar la cámara.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: Bus OV2640 integrado AI Thinker; USB mediante ESP32CAM-MB; sin GPIO externos.
# ============================================
# Sistemas Programables | PetCare | Equipo 08
# Prueba finita de OV2640: no necesita Wi-Fi ni activa otros componentes.
# Placa: ESP32-CAM AI Thinker con base USB ESP32CAM-MB.
# Pines: bus de camara integrado; no agregar cables GPIO para esta prueba.
import time
import sys

def probar():
    try:
        import camera
    except ImportError:
        print('FALTA EL MODULO camera: este firmware no incluye el controlador.')
        print('No es un fallo del cableado. No reinstalar firmware sin respaldo.')
        return
    try:
        try:
            camera.deinit()
        except Exception:
            pass
        camera.init(0, format=camera.JPEG, fb_location=camera.PSRAM)
        camera.framesize(camera.FRAME_VGA)
        camera.quality(12)
        time.sleep_ms(600)
        for n in range(3):
            foto = camera.capture()
            if not foto or foto[:2] != b'\xff\xd8' or foto[-2:] != b'\xff\xd9':
                raise OSError('Captura sin marcadores JPEG validos')
            print('Foto %d/3: JPEG de %d bytes OK' % (n + 1, len(foto)))
            time.sleep_ms(300)
        print('PRUEBA TERMINADA: sensor captura JPEG. Falta verificar imagen por Wi-Fi.')
    except KeyboardInterrupt:
        print('Prueba detenida por el usuario.')
    except Exception as error:
        sys.print_exception(error)
    finally:
        try:
            camera.deinit()
        except Exception:
            pass
        print('Camara liberada. La consola debe volver a >>>.')

probar()
