# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: test_ia_mqtt.py
# Objetivo: Probar frescura de imagen, señal limitada y confirmaciones.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; software en PC.
# ============================================
import importlib.util
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from ia_policy import DogSignalPolicy
from mqtt_camera import MQTTCameraStream
from petcare_server import PetCareBridge
from esp32_simulado import SensoresSimulados, SalidaSimulada
from controlador import PetCareController


def frame(number=1, dog=True, age=.2):
    return {'available': True, 'dog_detected': dog, 'frame_age_seconds': age,
            'processed_at': '2026-11-08T21:00:00+00:00', 'frame_number': number,
            'detections': [{'class': 'dog', 'confidence': .9}] if dog else [],
            'uncertain_detections': 0}


class IATests(unittest.TestCase):
    def test_cliente_esp32_envia_identidad_y_claves_como_bytes(self):
        import mqtt_link
        client=Mock();factory=Mock(return_value=client)
        with patch.dict(sys.modules,{'umqtt.simple':types.SimpleNamespace(MQTTClient=factory)}), \
             patch.object(mqtt_link.config,'MQTT_USER','usuario'), \
             patch.object(mqtt_link.config,'MQTT_PASSWORD','clave_de_prueba'):
            link=mqtt_link.MQTTLink();link._connect(0)
        self.assertIsInstance(factory.call_args.args[0],bytes)
        self.assertEqual(factory.call_args.kwargs['user'],b'usuario')
        self.assertEqual(factory.call_args.kwargs['password'],b'clave_de_prueba')

    def test_cliente_camara_usa_bytes_y_timeout(self):
        path=Path(__file__).resolve().parents[1]/'firmware/esp32cam/camara_mqtt.py'
        spec=importlib.util.spec_from_file_location('camera_mqtt_test',path)
        module=importlib.util.module_from_spec(spec)
        factory=Mock();settings=types.SimpleNamespace(HOST='localhost',USER='usuario',PASSWORD='clave_de_prueba')
        with patch.dict(sys.modules,{'uasyncio':types.SimpleNamespace(), 'umqtt.simple':types.SimpleNamespace(MQTTClient=factory)}):
            spec.loader.exec_module(module)
            module.PublicadorFrames(settings).conectar()
        self.assertIsInstance(factory.call_args.args[0],bytes)
        factory.return_value.connect.assert_called_once_with(timeout=2)

    def test_una_senal_por_presencia_y_rearme(self):
        policy = DogSignalPolicy()
        self.assertIsNotNone(policy.propose(frame(), 10))
        policy.accepted(10)
        self.assertIsNone(policy.propose(frame(2), 30))
        for n in range(3, 6): self.assertIsNone(policy.propose(frame(n, False), 30))
        self.assertIsNotNone(policy.propose(frame(6), 31))

    def test_cuadro_repetido_no_rearma(self):
        policy = DogSignalPolicy()
        policy.accepted(0)
        for _ in range(5): policy.propose(frame(1, False), 30)
        self.assertIsNone(policy.propose(frame(2), 31))

    def test_sin_imagen_o_vieja_no_dispara(self):
        policy = DogSignalPolicy()
        for age in (None, float('nan'), float('inf'), -1, 4):
            self.assertIsNone(policy.propose(frame(age=age), 100))
        value=frame(); value['available']=False
        self.assertIsNone(policy.propose(value, 100))

    def test_cooldown_y_clasificacion_dudosa(self):
        policy=DogSignalPolicy();policy.accepted(1);policy.armed=True
        self.assertIsNone(policy.propose(frame(), 2))
        value=frame(2);value['uncertain_detections']=1
        self.assertIsNone(policy.propose(value, 30))

    def test_senal_no_mueve_motores_y_se_apaga(self):
        outputs=[SalidaSimulada() for _ in range(4)]
        control=PetCareController(SensoresSimulados(), *outputs)
        control.tick(0)
        self.assertTrue(control.request_signal(0)[0])
        control.tick(1499);self.assertEqual(outputs[3].color,'white')
        control.tick(1500);self.assertNotEqual(outputs[3].color,'white')
        self.assertFalse(outputs[0].angles);self.assertFalse(outputs[1].active)

    def test_mqtt_link_real_deduplica_y_confirma(self):
        path=Path(__file__).resolve().parents[1]/'firmware/esp32/mqtt_link.py'
        spec=importlib.util.spec_from_file_location('hardware_mqtt_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        link=module.MQTTLink(); link.client=Mock()
        control=Mock();control.state='LISTO';control.request_signal.return_value=(True,'RGB')
        msg=b'{"id":"ia-test","action":"signal_dog"}'
        for now in (0, 50):
            link._on_message(link.command_topic,msg);link._run_command(control,now)
        control.request_signal.assert_called_once_with(0)
        self.assertEqual(link.client.publish.call_count,2)

    def test_camara_rechaza_retenidos_y_jpeg_invalido(self):
        camera=MQTTCameraStream({})
        for data, retain in [(b'no JPEG',False),(b'\xff\xd8abc\xff\xd9',True)]:
            camera._message(None,None,types.SimpleNamespace(topic=camera.topic,payload=data,retain=retain))
        self.assertEqual(camera.sequence,0)
        camera._message(None,None,types.SimpleNamespace(topic=camera.topic,payload=b'\xff\xd8abc\xff\xd9',retain=False))
        self.assertEqual(camera.sequence,1)
        camera.received_at=time.monotonic()-5
        self.assertIsNotNone(camera.latest(timeout=0)[3])

    def test_puente_envio_ack_y_firebase(self):
        db=Mock();bridge=PetCareBridge({'automation':{'dog_indicator_enabled':True}}, db)
        client=Mock();client.is_connected.return_value=True;client.publish.return_value.rc=0
        bridge.set_mqtt_client(client)
        command=bridge.process_vision(frame())
        self.assertEqual(command['action'],'signal_dog')
        self.assertFalse(client.publish.call_args.kwargs['retain'])
        self.assertEqual(client.publish.call_args.kwargs['qos'],0)
        bridge._queue_message((bridge.base_topic+'/ack',{'id':command['id'],'ok':True}))
        bridge.process_messages()
        self.assertNotIn(command['id'],bridge.pending_ia)
        self.assertTrue(any(call.args[0].endswith(command['id']) for call in db.patch.call_args_list))


if __name__ == '__main__': unittest.main()
