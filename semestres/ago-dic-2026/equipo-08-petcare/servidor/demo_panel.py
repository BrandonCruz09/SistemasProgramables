"""Demostracion local del panel y controlador. Sin MQTT, GPIO ni nube."""
import queue
import sys
import time
from pathlib import Path
from dashboard import DashboardState, start_dashboard

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'firmware' / 'esp32'))
import config
from controlador import PetCareController


class Sensors:
    def __init__(self): self.weight = 0.0
    def read(self, now):
        return dict(weight_g=self.weight, weight_control_g=self.weight,
                    weight_age_ms=0, calibrated=True, hx_ok=True, pir=False,
                    temperature_c=23.0, humidity_pct=55.0, dht_ok=True,
                    water_available=None, water_level_monitored=False)


class Servo:
    def __init__(self, sensors): self.sensors=sensors; self.open=False
    def move_us(self, pulse):
        if pulse == config.SERVO_CLOSED_US and self.open:
            self.sensors.weight += 60.0  # Ejemplo simulado; no es caudal medido.
        self.open = pulse == config.SERVO_OPEN_US
    def release(self): pass


class Output:
    def __init__(self): self.active=False
    def on(self, duration_ms=None): self.active=True
    def off(self): self.active=False
    def set_color(self, color): self.color=color


class DemoState(DashboardState):
    def request_command(self, action, supervised=False):
        if action == 'reset_demo':
            try: self.commands.put_nowait({'action':action})
            except queue.Full: return False, 'Espera un momento'
            return True, 'Reiniciando solo la simulacion'
        return super().request_command(action, supervised)


def main():
    config.SERVO_MOVEMENT_ENABLED=True  # Solo este proceso; no escribe config.py.
    state=DemoState()
    def controller():
        sensors=Sensors()
        return PetCareController(sensors,Servo(sensors),Output(),Output(),Output())
    c=controller()
    server=start_dashboard(state,ROOT/'interfaz/dashboard.html','127.0.0.1',8770,demo_mode=True)
    print('SIMULACION http://127.0.0.1:8770/',flush=True)
    try:
        while True:
            now=int(time.monotonic()*1000)
            c.tick(now)
            try: command=state.commands.get_nowait()
            except queue.Empty: command=None
            if command:
                action=command['action']
                if action=='reset_demo': c.safe_shutdown(); c=controller(); c.tick(now); ok,msg=True,'Simulacion reiniciada'
                elif action=='feed': ok,msg=c.request_food(now)
                elif action=='water': ok,msg=c.request_pump(now)
                elif action=='stop_food': ok,msg=c.stop_food(now)
                elif action=='stop_water': c.stop_pump(now); ok,msg=True,'Agua detenida (simulacion)'
                else: ok,msg=c.request_signal(now)
                state.events.append({'id':action,'ok':ok,'message':msg})
            state.update({'simulated':True,'status':c.snapshot()})
            time.sleep(.05)
    finally: c.safe_shutdown(); server.shutdown(); server.server_close()


if __name__=='__main__': main()
