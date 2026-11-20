"""MQTT 3.1.1 local. Recepcion incremental para no bloquear los actuadores."""

import json
import time
import config


def string(value):
    value = value.encode() if isinstance(value, str) else value
    return bytes((len(value) >> 8, len(value) & 255)) + value


def packet(header, body):
    size = len(body)
    length = bytearray()
    while True:
        b = size % 128
        size //= 128
        length.append(b | 128 if size else b)
        if not size:
            break
    return bytes((header,)) + length + body


def take_packet(buffer):
    if len(buffer) < 2:
        return None
    size = 0
    multiplier = 1
    pos = 1
    for _ in range(4):
        if pos >= len(buffer):
            return None
        b = buffer[pos]
        pos += 1
        size += (b & 127) * multiplier
        if not b & 128:
            break
        multiplier *= 128
    else:
        raise ValueError("Longitud MQTT invalida")
    if size > 8192:
        raise ValueError("Paquete MQTT demasiado grande")
    if len(buffer) < pos + size:
        return None
    result = (buffer[0], bytes(buffer[pos : pos + size]), pos + size)
    return result


class MQTTLink:
    def __init__(self):
        self.sock = None
        self.rx = bytearray()
        self.tx = bytearray()
        self.retry = 0
        self.last_publish = None
        self.last_ping = 0
        self.last_rx = 0
        self.base = config.MQTT_BASE_TOPIC
        self.recent = []
        self.water_id = None
        self.water_sent = None
        self.connected = False

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None
        self.connected = False
        self.rx = bytearray()
        self.tx = bytearray()
        self.water_sent = None

    def connect(self, now):
        import socket

        self.retry = time.ticks_add(now, 10000)
        s = socket.socket()
        s.settimeout(1)
        self.sock = s
        address = socket.getaddrinfo(config.MQTT_HOST, config.MQTT_PORT)[0][-1]
        s.connect(address)
        flags = 2 | (0xC0 if config.MQTT_USER else 0)
        body = string("MQTT") + bytes((4, flags, 0, 30)) + string(config.MQTT_CLIENT_ID)
        if config.MQTT_USER:
            body += string(config.MQTT_USER) + string(config.MQTT_PASSWORD)
        s.sendall(packet(0x10, body))
        answer = b""
        while len(answer) < 4:
            chunk = s.recv(4 - len(answer))
            if not chunk:
                raise OSError("MQTT cerro conexion")
            answer += chunk
        if answer != b"\x20\x02\x00\x00":
            raise OSError("MQTT rechazo conexion")
        s.setblocking(False)
        self.tx.extend(packet(0x82, b"\x00\x02" + string(self.base + "/commands") + b"\x00"))
        self.connected = True
        self.last_publish = None
        self.last_rx = self.last_ping = time.ticks_ms()
        print("MQTT conectado; control disponible")

    def publish(self, suffix, data, qos=0):
        body = string(self.base + "/" + suffix)
        if qos:
            body += b"\x00\x01"
        msg = packet(0x32 if qos else 0x30, body + json.dumps(data).encode())
        if len(self.tx) + len(msg) > 16384:
            raise OSError("Cola MQTT llena")
        self.tx.extend(msg)

    def receive(self, header, body, controller, now):
        kind = header >> 4
        if kind == 4 and body == b"\x00\x01":
            if controller.water_events and controller.water_events[0]["id"] == self.water_id:
                controller.water_events.pop(0)
            self.water_id = self.water_sent = None
            return
        if kind != 3:
            return
        if len(body) < 2:
            raise ValueError("Mensaje MQTT incompleto")
        n = (body[0] << 8) | body[1]
        topic = body[2 : 2 + n]
        pos = 2 + n
        qos = (header >> 1) & 3
        if qos == 1:
            if len(body) < pos + 2:
                raise ValueError("Identificador MQTT incompleto")
            self.tx.extend(packet(0x40, body[pos : pos + 2]))
            pos += 2
        if topic != (self.base + "/commands").encode() or header & 1:
            return
        try:
            data = json.loads(body[pos:])
            if not isinstance(data, dict):
                return
            cid = data.get("id")
            action = data.get("action")
            if not isinstance(cid, str) or not cid or len(cid) > 64:
                return
            if cid in self.recent:
                ok, message = False, "Comando repetido; no se ejecuta otra vez"
            elif (
                action not in ("stop_water", "stop_food", "signal_dog")
                and data.get("session_id") != controller.session
            ):
                ok, message = False, "Sesion antigua; actualiza la pagina"
            elif action == "water" and data.get("supervised") is not True:
                ok, message = False, "Confirma agua en deposito y espacio en tazon"
            else:
                self.recent = (self.recent + [cid])[-32:]
                ok, message = controller.command(action, now, cid)
            self.publish(
                "ack",
                {
                    "id": cid,
                    "action": action,
                    "ok": bool(ok),
                    "message": message,
                    "state": controller.state,
                    "physical_verified": False,
                },
            )
            self.last_publish = None
        except (ValueError, TypeError, KeyError) as exc:
            print("Comando MQTT invalido:", repr(exc))

    def poll(self, now, controller, wifi_ok):
        if not config.MQTT_HOST or not wifi_ok:
            if self.sock:
                self.close()
            return
        try:
            if self.sock is None:
                if not controller.action_in_progress() and time.ticks_diff(now, self.retry) >= 0:
                    self.connect(now)
                return
            for _ in range(4):
                try:
                    chunk = self.sock.recv(1024)
                except OSError as exc:
                    if exc.args[0] in (11, 35, 116):
                        break
                    raise
                if not chunk:
                    raise OSError("MQTT desconectado")
                self.rx.extend(chunk)
                self.last_rx = now
                if len(self.rx) > 10000:
                    raise ValueError("Recepcion MQTT excesiva")
            for _ in range(4):
                item = take_packet(self.rx)
                if item is None:
                    break
                self.rx = self.rx[item[2] :]
                self.receive(item[0], item[1], controller, now)
            if self.last_publish is None or time.ticks_diff(now, self.last_publish) >= 2000:
                self.publish(
                    "telemetry",
                    {"device": "esp32-devkit", "uptime_ms": now, "status": controller.snapshot()},
                )
                self.last_publish = now
            if controller.water_events and (
                self.water_sent is None or time.ticks_diff(now, self.water_sent) >= 3000
            ):
                event = controller.water_events[0]
                self.water_id = event["id"]
                self.water_sent = now
                self.publish("water_events", event, qos=1)
            if time.ticks_diff(now, self.last_ping) >= 15000:
                self.tx.extend(b"\xc0\x00")
                self.last_ping = now
            if time.ticks_diff(now, self.last_rx) > 45000:
                raise OSError("MQTT sin respuesta al ping")
            if self.tx:
                try:
                    count = self.sock.send(self.tx)
                    if count:
                        self.tx = self.tx[count:]
                except OSError as exc:
                    if exc.args[0] not in (11, 35, 116):
                        raise
        except Exception as exc:
            print("MQTT:", repr(exc))
            self.close()
            self.retry = time.ticks_add(now, 10000)
