# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: camara_wifi.py
# Objetivo: Servir video MJPEG y fotografias por Wi-Fi.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: OV2640 integrada; USB mediante ESP32CAM-MB.
# ============================================
import camera
import network
import time
import gc
import uasyncio as asyncio
from wifi_config import SSID, PASSWORD

FRAME_INTERVAL_MS = 250
MAX_JPEG_BYTES = 200000


def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        inicio = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), inicio) > 25000:
                raise OSError('Wi-Fi no disponible; revisa la red de 2.4 GHz')
            time.sleep_ms(200)
    return wlan.ifconfig()[0]


def iniciar_camara():
    try:
        camera.deinit()
    except Exception:
        pass
    camera.init(0, format=camera.JPEG, fb_location=camera.PSRAM)
    camera.framesize(camera.FRAME_VGA)
    camera.quality(12)
    time.sleep_ms(600)


class ServidorCamara:
    def __init__(self):
        self.stream_activo = False
        self.captura_lock = asyncio.Lock()
        self.server = None
        self.clients = set()

    async def cerrar(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for writer in list(self.clients):
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), 1)
            except Exception:
                pass
        self.clients.clear()

    async def enviar(self, writer, data):
        # Los bloques cortos permiten atender STOP y clientes lentos.
        for pos in range(0, len(data), 4096):
            writer.write(data[pos:pos + 4096])
            await asyncio.wait_for(writer.drain(), 3)

    async def capturar(self):
        async with self.captura_lock:
            jpeg = camera.capture()
            if not jpeg or len(jpeg) > MAX_JPEG_BYTES or jpeg[:2] != b'\xff\xd8':
                raise OSError('Captura JPEG invalida')
            return jpeg

    async def respuesta(self, writer, status, content_type, data):
        header = ('HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n'
                  'Cache-Control: no-store\r\nConnection: close\r\n\r\n'
                  % (status, content_type, len(data))).encode()
        await self.enviar(writer, header)
        await self.enviar(writer, data)

    async def video(self, writer):
        if self.stream_activo:
            await self.respuesta(writer, '503 Service Unavailable', 'text/plain',
                                 b'Video ocupado. Usa la pagina de la PC o cierra el otro visor.')
            return
        self.stream_activo = True
        try:
            await self.enviar(writer, b'HTTP/1.1 200 OK\r\nCache-Control: no-store\r\n'
                              b'Content-Type: multipart/x-mixed-replace; boundary=frame\r\n'
                              b'Connection: close\r\n\r\n')
            while True:
                jpeg = await self.capturar()
                header = b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n' % len(jpeg)
                await self.enviar(writer, header)
                await self.enviar(writer, jpeg)
                await self.enviar(writer, b'\r\n')
                del jpeg
                gc.collect()
                await asyncio.sleep_ms(FRAME_INTERVAL_MS)
        finally:
            self.stream_activo = False

    async def atender(self, reader, writer):
        self.clients.add(writer)
        try:
            request = await asyncio.wait_for(reader.readline(), 3)
            if len(request) > 512:
                return
            parts = request.split()
            if len(parts) != 3 or parts[0] != b'GET':
                await self.respuesta(writer, '405 Method Not Allowed', 'text/plain', b'Solo GET')
                return
            path = parts[1].split(b'?')[0]
            total = 0
            for _ in range(32):
                line = await asyncio.wait_for(reader.readline(), 3)
                total += len(line)
                if total > 4096:
                    return
                if line in (b'\r\n', b'\n', b''):
                    break
            else:
                return
            if path == b'/stream':
                await self.video(writer)
            elif path == b'/foto':
                await self.respuesta(writer, '200 OK', 'image/jpeg', await self.capturar())
            elif path == b'/health':
                await self.respuesta(writer, '200 OK', 'application/json', b'{"camera":"ok"}')
            elif path == b'/':
                pagina = ("<!doctype html><html lang='es'><meta charset='utf-8'>"
                          "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                          "<title>PetCare Camara</title><body style='font:18px sans-serif;padding:20px'>"
                          '<h1>PetCare</h1><p>Camara conectada.</p>'
                          "<p><a href='/stream'>Ver video sin detecciones</a></p>"
                          "<p><a href='/foto'>Tomar una foto</a></p>"
                          '<p>Para ver perros y personas, abre la pagina de la PC.</p></body></html>')
                await self.respuesta(writer, '200 OK', 'text/html; charset=utf-8', pagina.encode())
            else:
                await self.respuesta(writer, '404 Not Found', 'text/plain', b'Ruta no encontrada')
        except (OSError, asyncio.TimeoutError):
            pass
        except Exception as error:
            print('HTTP/camara:', error)
        finally:
            self.clients.discard(writer)
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), 1)
            except Exception:
                pass

    async def ejecutar(self, ip):
        server = await asyncio.start_server(self.atender, ip, 80, backlog=3)
        self.server = server
        print('PetCare: http://%s/ | video: /stream | foto: /foto' % ip)
        print('Detener: STOP de Thonny o Ctrl+C.')
        mqtt_task = None
        publisher = None
        try:
            import mqtt_config
            if mqtt_config.ENABLED and mqtt_config.HOST:
                from camara_mqtt import PublicadorFrames
                publisher = PublicadorFrames(mqtt_config)
                mqtt_task = asyncio.create_task(publisher.ejecutar(self.capturar))
        except ImportError:
            print('MQTT opcional no configurado; usando HTTP.')
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            if mqtt_task:
                mqtt_task.cancel()
                try:
                    await mqtt_task
                except asyncio.CancelledError:
                    pass
            if publisher:
                publisher.cerrar()
            server.close()
            await server.wait_closed()


def main():
    app = ServidorCamara()
    try:
        ip = conectar_wifi()
        iniciar_camara()
        asyncio.run(app.ejecutar(ip))
    except KeyboardInterrupt:
        print('Camara detenida.')
    except Exception as error:
        print('No se pudo iniciar:', error)
    finally:
        try:
            asyncio.run(app.cerrar())
        except Exception as error:
            print('Cierre de red:', error)
        asyncio.new_event_loop()
        try:
            camera.deinit()
        except Exception:
            pass
        gc.collect()


if __name__ == '__main__':
    main()
