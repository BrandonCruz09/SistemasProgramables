"""Wi-Fi con reintento y panel local; peticiones pequenas con plazo limitado."""

import time
import json
import config

HTML = """<!doctype html><html lang="es"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PetCare local</title><style>body{font:18px sans-serif;background:#f5f1e8;color:#253b35;max-width:760px;margin:32px auto;padding:16px}button{padding:14px;margin:6px;border-radius:12px;border:1px solid #888}pre{white-space:pre-wrap}</style><h1>PetCare · Control local</h1><p>El peso se lee con la calibracion guardada. Agua: 5 segundos, sin medir volumen.</p><button onclick="cmd('gate_open')">Abrir compuerta</button><button onclick="cmd('gate_close')">Cerrar compuerta</button><button onclick="cmd('feed')">Completar 300 g</button><button onclick="cmd('stop_food')">Detener alimento</button><br><label><input id="agua" type="checkbox">Bomba sumergida y espacio en el tazon</label><br><button onclick="cmd('water')">Agua 5 s</button><button onclick="cmd('stop_water')">Detener agua</button><button onclick="cmd('beep')">Pitido activo</button><button onclick="cmd('beep','passive')">Probar tono pasivo</button><p id="msg"></p><pre id="datos"></pre><script>let sid='';async function update(){try{let r=await fetch('/api');let s=await r.json();sid=s.session_id;datos.textContent=JSON.stringify(s,null,2)}catch(e){msg.textContent='Sin conexion'}}async function cmd(action,mode){try{let r=await fetch('/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,mode,session_id:sid,supervised:agua.checked})});msg.textContent=(await r.json()).message;await update()}catch(e){msg.textContent='Sin confirmacion'}}update();setInterval(update,1500)</script></html>"""


class Wifi:
    def __init__(self):
        self.wlan = None
        self.retry = 0
        self.started = None
        if config.WIFI_SSID:
            try:
                import network

                self.wlan = network.WLAN(network.STA_IF)
            except Exception as exc:
                print("Wi-Fi:", repr(exc))

    def connected(self):
        try:
            return self.wlan is not None and self.wlan.isconnected()
        except OSError:
            return False

    def tick(self, now, idle=True):
        if self.wlan is None or self.connected() or not idle:
            return
        try:
            if self.started is not None and time.ticks_diff(now, self.started) < 10000:
                return
            if time.ticks_diff(now, self.retry) < 0:
                return
            self.wlan.active(False)
            self.wlan.active(True)
            self.wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            self.started = now
            self.retry = time.ticks_add(now, 15000)
        except OSError as exc:
            print("Wi-Fi:", repr(exc))
            self.retry = time.ticks_add(now, 15000)


class WebDashboard:
    def __init__(self):
        self.server = self.client = None
        self.buffer = bytearray()
        self.output = b""
        self.started = 0

    def start(self):
        import socket

        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", config.WEB_PORT))
        self.server.listen(2)
        self.server.setblocking(False)

    def finish(self):
        if self.client:
            try:
                self.client.close()
            except OSError:
                pass
        self.client = None
        self.buffer = bytearray()
        self.output = b""

    def poll(self, controller, now):
        if self.server is None:
            return
        try:
            if self.client is None:
                try:
                    self.client, _ = self.server.accept()
                except OSError:
                    return
                self.client.setblocking(False)
                self.started = now
            if time.ticks_diff(now, self.started) > 2000:
                self.finish()
                return
            if self.output:
                try:
                    n = self.client.send(self.output)
                    self.output = self.output[n:]
                    if not self.output:
                        self.finish()
                except OSError as exc:
                    if exc.args[0] not in (11, 35, 116):
                        raise
                return
            try:
                data = self.client.recv(512)
            except OSError as exc:
                if exc.args[0] in (11, 35, 116):
                    return
                raise
            if not data:
                self.finish()
                return
            self.buffer.extend(data)
            if len(self.buffer) > 4096:
                self.finish()
                return
            end = self.buffer.find(b"\r\n\r\n")
            if end < 0:
                return
            header = bytes(self.buffer[:end]).decode()
            lines = header.split("\r\n")
            method, path, _ = lines[0].split(" ")
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.lower()] = v.strip()
            length = int(headers.get("content-length", "0"))
            if length < 0 or length > 1024:
                self.finish()
                return
            if len(self.buffer) < end + 4 + length:
                return
            mime = "application/json"
            status = "200 OK"
            if method == "GET" and path == "/":
                body = HTML
                mime = "text/html; charset=utf-8"
            elif method == "GET" and path == "/api":
                body = json.dumps(controller.snapshot())
            elif method == "POST" and path == "/command":
                d = json.loads(bytes(self.buffer[end + 4 : end + 4 + length]))
                if d.get("session_id") != controller.session:
                    ok, msg = False, "Actualiza la pagina"
                elif d.get("action") == "water" and d.get("supervised") is not True:
                    ok, msg = False, "Confirma la bomba y el tazon"
                else:
                    ok, msg = controller.command(d.get("action"), now, mode=d.get("mode"))
                body = json.dumps({"ok": ok, "message": msg})
            else:
                status = "404 Not Found"
                body = "{}"
            payload = body.encode()
            self.output = (
                "HTTP/1.1 "
                + status
                + "\r\nContent-Type: "
                + mime
                + "\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: "
                + str(len(payload))
                + "\r\n\r\n"
            ).encode() + payload
        except Exception as exc:
            print("Panel:", repr(exc))
            self.finish()

    def close(self):
        self.finish()
        if self.server:
            self.server.close()
        self.server = None
