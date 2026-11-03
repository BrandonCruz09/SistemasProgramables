# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: camara_wifi.py
# Objetivo: Servir fotografías JPEG por HTTP con VGA y cierre de recursos.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: Bus OV2640 integrado AI Thinker; alimentación/programación por base ESP32CAM-MB.
# ============================================
# ESP32-CAM S1 / ESP32 clasico con camara OV2640
# Configura tu red Wi-Fi antes de ejecutar.
from wifi_config import SSID, PASSWORD
import camera
import network
import socket
import time





def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        inicio = time.time()
        while not wlan.isconnected():
            if time.time() - inicio > 25:
                raise OSError("No se pudo conectar al Wi-Fi. Revisa SSID y contrasena.")
            print("Conectando a Wi-Fi...")
            time.sleep(1)
    ip = wlan.ifconfig()[0]
    print("Wi-Fi conectado. IP:", ip)
    return ip


def iniciar_camara():
    try:
        camera.deinit()
    except Exception:
        pass
    # Configuracion predeterminada ESP32-CAM (AI Thinker y placas compatibles).
    camera.init(0, format=camera.JPEG, fb_location=camera.PSRAM)
    camera.framesize(camera.FRAME_VGA)
    camera.quality(12)
    time.sleep_ms(600)
    print("Camara OV2640 lista: VGA 640x480, calidad JPEG 12")


def responder(conn, solicitud):
    if b"GET /foto" in solicitud:
        try:
            foto = camera.capture()
            if not foto:
                raise OSError("Captura vacia")
            conn.write(b"HTTP/1.1 200 OK\r\n")
            conn.write(b"Content-Type: image/jpeg\r\n")
            conn.write(b"Cache-Control: no-store\r\n")
            conn.write(b"Content-Length: %d\r\n\r\n" % len(foto))
            conn.write(foto)
        except Exception as error:
            print("Error al capturar:", error)
            conn.write(b"HTTP/1.1 500 Internal Server Error\r\n")
            conn.write(b"Content-Type: text/plain\r\nConnection: close\r\n\r\n")
            conn.write(b"Error al tomar la foto")
    else:
        pagina = ("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n"
                  "Connection: close\r\n\r\n"
                  "<html><meta name='viewport' content='width=device-width'>"
                  "<h1>PetCare - Camara</h1>"
                  "<p><a href='/foto'>Tomar y ver una foto</a></p></html>")
        conn.write(pagina.encode())


def iniciar_servidor(ip):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((ip, 80))
        servidor.listen(2)
        servidor.settimeout(1)
        print("PETCARE: abre http://%s/ en la misma red Wi-Fi" % ip)
        print("Detener: boton STOP de Thonny o Ctrl+C en consola.")
        while True:
            try:
                conn, direccion = servidor.accept()
            except OSError as error:
                if error.args and error.args[0] in (11, 110, 116):
                    continue
                raise
            try:
                conn.settimeout(3)
                solicitud = conn.recv(1024)
                if solicitud:
                    responder(conn, solicitud)
            except Exception as error:
                print("Error HTTP:", error)
            finally:
                conn.close()
    finally:
        servidor.close()

# Datos privados de la red local. No publicar este archivo con credenciales.



try:
    ip = conectar_wifi()
    iniciar_camara()
    iniciar_servidor(ip)
except KeyboardInterrupt:
    print("Servidor detenido por el usuario.")
except Exception as error:
    print("Error de inicio:", error)
finally:
    try:
        camera.deinit()
    except Exception:
        pass
    print("Camara liberada; puedes volver a ejecutar con F5.")
