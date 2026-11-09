# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: wifi_panel.py
# Objetivo: Conectar Wi-Fi y servir el panel local de control.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: DHT22=4, PIR=27, HX711 DT/SCK=19/18, flotador=26, servo MG995=33, bomba MOSFET=23, buzzer=22, RGB=16/17/21
# ============================================
# PetCare - Wi-Fi opcional y panel web local, sin dependencias externas.
import config

HTML = """<!doctype html><html lang='es'><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>PetCare | Equipo 08</title>
<style>body{font:16px Arial;background:#eef5f7;color:#183746;margin:24px;max-width:720px}main{background:white;border-radius:16px;padding:20px;box-shadow:0 4px 20px #aac}button{padding:14px;margin:6px;border:0;border-radius:10px;background:#087e83;color:white;font-weight:bold}pre{white-space:pre-wrap;background:#edf4f6;padding:12px;border-radius:8px}</style>
<main><h1>PetCare | Equipo 08</h1><p>Panel local de alimentacion e hidratacion</p>
<button onclick=\"fetch('/feed',{method:'POST'}).then(refresh)\">Servir una racion</button>
<button onclick=\"fetch('/pump',{method:'POST'}).then(refresh)\">Pulso de agua</button>
<button onclick=\"fetch('/pump/stop',{method:'POST'}).then(refresh)\">Detener bomba</button>
<pre id='status'>Cargando...</pre></main>
<script>async function refresh(){try{let r=await fetch('/api');let d=await r.json();document.querySelector('#status').textContent=JSON.stringify(d,null,2)}catch(e){document.querySelector('#status').textContent='Sin conexion con PetCare'}}refresh();setInterval(refresh,2000)</script></html>"""


def connect_wifi():
    if not config.WIFI_SSID or not config.WIFI_PASSWORD:
        print("Wi-Fi omitido: completa WIFI_SSID y WIFI_PASSWORD en config.py si deseas el panel.")
        return None, None
    import network
    import time
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        start = time.ticks_ms()
        while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start) < config.WIFI_CONNECT_TIMEOUT_MS:
            time.sleep_ms(200)
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("Panel PetCare: http://%s/" % ip)
        return wlan, ip
    print("No se conecto al Wi-Fi; PetCare seguira funcionando por USB.")
    return None, None


class WebDashboard:
    def __init__(self, port=config.WEB_PORT):
        self.port = port
        self.server = None

    def start(self):
        import socket
        self.server = socket.socket()
        try:
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        self.server.bind(("0.0.0.0", self.port))
        self.server.listen(1)
        self.server.settimeout(0)

    def poll(self, controller):
        if self.server is None:
            return
        try:
            client, _addr = self.server.accept()
        except Exception:
            return
        try:
            client.settimeout(0.15)
            request = client.recv(512).decode()
            first = request.split("\r\n", 1)[0]
            parts = first.split(" ")
            method = parts[0] if len(parts) > 0 else "GET"
            path = parts[1] if len(parts) > 1 else "/"
            now = __import__("time").ticks_ms()
            if path.startswith("/api"):
                body = __import__("json").dumps(controller.snapshot())
                self._send(client, "200 OK", "application/json", body)
            elif path.startswith("/feed") and method == "POST":
                ok, msg = controller.request_feed(now)
                self._send(client, "200 OK" if ok else "409 Conflict", "text/plain; charset=utf-8", msg)
            elif path.startswith("/pump/stop") and method == "POST":
                controller.stop_pump()
                self._send(client, "200 OK", "text/plain; charset=utf-8", "Bomba detenida")
            elif path.startswith("/pump") and method == "POST":
                ok, msg = controller.request_pump(now)
                self._send(client, "200 OK" if ok else "409 Conflict", "text/plain; charset=utf-8", msg)
            else:
                self._send(client, "200 OK", "text/html; charset=utf-8", HTML)
        except Exception:
            pass
        finally:
            try:
                client.close()
            except Exception:
                pass

    @staticmethod
    def _send(client, status, content_type, body):
        data = body.encode()
        header = "HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n" % (status, content_type, len(data))
        client.sendall(header.encode() + data)

    def close(self):
        if self.server is not None:
            self.server.close()
            self.server = None
