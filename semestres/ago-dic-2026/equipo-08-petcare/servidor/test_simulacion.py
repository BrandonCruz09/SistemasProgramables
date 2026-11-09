# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: test_simulacion.py
# Objetivo: Verificar aislamiento de simulacion y compatibilidad MQTT v2.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; pruebas de software.
# ============================================
import unittest
from unittest.mock import Mock
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.packettypes import PacketTypes
from petcare_server import PetCareBridge
from esp32_simulado import ESP32Simulado


class SimulationTests(unittest.TestCase):
    def test_simulator_rejects_hardware_topic(self):
        with self.assertRaises(ValueError): ESP32Simulado('petcare/equipo8')

    def test_simulated_payload_uses_its_own_database_path(self):
        cloud = Mock()
        bridge = PetCareBridge({'mqtt':{'base_topic':'petcare/equipo8/simulacion/demo'},
                                'firebase_root':'petcare/equipo8/simulacion/demo'}, cloud)
        payload = {'simulated':True,'status':{'weight_g':75}}
        bridge._queue_message((bridge.base_topic+'/telemetry',payload))
        bridge.process_messages()
        paths = [call.args[0] for call in cloud.put.call_args_list]
        self.assertIn('petcare/equipo8/simulacion/demo/latest', paths)
        self.assertTrue(all(path.startswith('petcare/equipo8/simulacion/demo/') for path in paths))
        self.assertTrue(cloud.put.call_args.args[1]['simulated'])

    def test_mqtt_v2_reason_code_subscribes_correct_topic(self):
        bridge = PetCareBridge({'mqtt':{'base_topic':'petcare/equipo8/simulacion/demo'}})
        client = Mock()
        bridge.on_connect(client,None,None,ReasonCode(PacketTypes.CONNACK,'Success'),None)
        self.assertEqual(client.subscribe.call_args.args[0][0][0],bridge.base_topic+'/telemetry')


if __name__=='__main__': unittest.main()
