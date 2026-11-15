# Sistemas Programables | PetCare | Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez.
# Objetivo: capturar sensores reales con el mismo SensorHub usado por main.py.
# Pines: HX711 DT19/SCK18, DHT22 DATA4, PIR27. No inicializa actuadores.
import time
import json
import config
from sensores import SensorHub

hub = SensorHub()
samples = []
for index in range(12):
    status = hub.read(time.ticks_ms())
    if status['hx_ok'] and status['weight_g'] is not None:
        samples.append(status.copy())
        print('PESO_INTEGRADO_G', status['weight_g'])
    time.sleep_ms(850)
if len(samples) < 5:
    raise ValueError('No hay suficientes lecturas reales validas')
payload = {'device': 'esp32-devkit', 'simulated': False,
           'source': 'esp32_usb_sensorhub', 'transport_to_pc': 'USB_serial',
           'actuators_initialized': False, 'status': samples[-1]}
print('PESA_CAPTURA', json.dumps({'payload': payload, 'samples': samples,
      'tare_raw': config.TARE_RAW, 'factor': config.CALIBRATION_FACTOR}))
