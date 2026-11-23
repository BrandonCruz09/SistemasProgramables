# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: test_dashboard.py
# Objetivo: Verificar estado, histórico limitado y respuesta HTTP del panel.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; software en PC.
# ============================================
import json
import sys
import time
import types
import unittest
import urllib.request
from pathlib import Path
from dashboard import DashboardState, start_dashboard
from unittest.mock import Mock, patch


class DashboardTests(unittest.TestCase):
    def test_inicio_no_depende_de_dns_inversa(self):
        with patch('socket.getfqdn',side_effect=RuntimeError('DNS bloqueado')):
            server=start_dashboard(DashboardState(),Path(__file__).resolve().parents[1]/'interfaz/dashboard.html','0.0.0.0',0)
            server.shutdown();server.server_close()

    def test_no_inventa_datos_al_arrancar(self):
        state=DashboardState().snapshot()
        self.assertFalse(state['available'])
        self.assertIsNone(state['telemetry'])
        self.assertEqual(state['history'],[])

    def test_deslizador_rechaza_fuera_de_recorrido_y_encola_pulso_valido(self):
        state=DashboardState()
        state.update({'status':{
            'state':'LISTO','session_id':'servo-session','actions_allowed':True,
            'servo_manual_enabled':True,'servo_open_us':850,'servo_closed_us':1500,
            'hx_ok':True,'calibrated':True,'food_active':False,'pump_active':False,
        }})
        self.assertFalse(state.request_command('gate_position',position_us=800)[0])
        self.assertFalse(state.request_command('gate_position',position_us=1550)[0])
        self.assertTrue(state.request_command('gate_position',position_us=1200)[0])
        queued=state.commands.get_nowait()
        self.assertEqual(queued['action'],'gate_position')
        self.assertEqual(queued['position_us'],1200)
        self.assertEqual(queued['session_id'],'servo-session')

    def test_deslizador_no_acepta_peso_no_calibrado_ni_bomba_activa(self):
        state=DashboardState()
        base={'state':'LISTO','session_id':'servo-session','actions_allowed':True,
              'servo_manual_enabled':True,'servo_open_us':850,'servo_closed_us':1500,
              'hx_ok':True,'calibrated':True,'food_active':False,'pump_active':False}
        state.update({'status':dict(base,calibrated=False)})
        self.assertFalse(state.request_command('gate_position',position_us=1200)[0])
        state.update({'status':dict(base,pump_active=True)})
        self.assertFalse(state.request_command('gate_position',position_us=1200)[0])

    def test_automatico_requiere_orden_explicita_y_estado_reciente(self):
        state=DashboardState()
        state.update({'status':{'state':'LISTO','session_id':'abc','auto_serve_available':True,
                                'auto_serve_enabled':False,'actions_allowed':True}})
        self.assertTrue(state.request_command('auto_enable')[0])
        enable=state.commands.get_nowait()
        self.assertEqual(enable['action'],'auto_enable')
        self.assertEqual(enable['session_id'],'abc')
        state.command_sent('e1','auto_enable','now')
        state.command_ack({'id':'e1','ok':True,'action':'auto_enable'},'later')
        self.assertTrue(state.snapshot()['automation_armed'])
        state.update({'status':{'state':'BOMBA_ACTIVA','session_id':'abc','auto_serve_available':True,
                                'auto_serve_enabled':True,'actions_allowed':True}})
        self.assertTrue(state.request_command('auto_disable')[0])
        self.assertEqual(state.commands.get_nowait()['action'],'auto_disable')
        state.command_sent('e2','auto_disable','now')
        state.command_ack({'id':'e2','ok':True,'action':'auto_disable'},'later')
        self.assertFalse(state.snapshot()['automation_armed'])
        state.update({'status':{'state':'LISTO','session_id':'abc','auto_serve_available':False,
                                'auto_serve_enabled':False,'actions_allowed':True}})
        self.assertFalse(state.request_command('auto_enable')[0])

    def test_ia_no_publica_senales_hasta_ack_de_activacion(self):
        with patch.dict(sys.modules, {'requests':types.SimpleNamespace()}):
            from petcare_server import PetCareBridge
            bridge=PetCareBridge({'automation':{'dog_indicator_enabled':True}})
        client=Mock();client.is_connected.return_value=True;client.publish.return_value.rc=0
        bridge.set_mqtt_client(client)
        frame={'available':True,'frame_age_seconds':0.1,'processed_at':'test','frame_number':1,
               'dog_detected':True,'detections':[{'class':'dog','confidence':0.9}],
               'uncertain_detections':0}
        self.assertIsNone(bridge.process_vision(frame))
        bridge.dashboard.update({'status':{'state':'LISTO','session_id':'session1',
            'actions_allowed':True,'auto_serve_available':True,'auto_serve_enabled':False}})
        self.assertTrue(bridge.dashboard.request_command('auto_enable')[0])
        bridge.process_manual_commands()
        order=json.loads(client.publish.call_args.args[1])
        self.assertEqual(order['action'],'auto_enable')
        bridge.dashboard.command_ack({'id':order['id'],'action':'auto_enable','ok':True},'now')
        frame['frame_number']=2
        self.assertEqual(bridge.process_vision(frame)['action'],'signal_dog')

    def test_historico_limitado_y_dato_caducado(self):
        state=DashboardState()
        for n in range(140):state.update({'simulated':True,'status':{'weight_g':n}})
        self.assertEqual(len(state.snapshot()['history']),120)
        self.assertEqual(state.snapshot()['history'][0]['status']['weight_g'],20)
        state.received=time.monotonic()-31
        self.assertFalse(state.snapshot()['available'])

    def test_historial_recuperado_no_finge_telemetria_viva(self):
        state=DashboardState();state.restore_history({'1':{'status':{'weight_g':12}}})
        self.assertEqual(len(state.snapshot()['history']),1)
        self.assertFalse(state.snapshot()['available'])

    def test_pagina_y_api_http(self):
        state=DashboardState();state.update({'simulated':True,'status':{'weight_g':None}})
        server=start_dashboard(state,Path(__file__).resolve().parents[1]/'interfaz/dashboard.html','127.0.0.1',0)
        try:
            base='http://127.0.0.1:'+str(server.server_port)
            self.assertIn('Estado de la estación',urllib.request.urlopen(base,timeout=2).read().decode())
            data=json.load(urllib.request.urlopen(base+'/api/state',timeout=2))
            self.assertTrue(data['telemetry']['simulated'])
            self.assertIsNone(data['telemetry']['status']['weight_g'])
            self.assertNotIn('password',data)
        finally:
            server.shutdown();server.server_close()


    def test_demo_y_archivos_publicos(self):
        server=start_dashboard(DashboardState(),Path(__file__).resolve().parents[1]/'interfaz/dashboard.html','127.0.0.1',0,demo_mode=True)
        try:
            base='http://127.0.0.1:'+str(server.server_port)
            with urllib.request.urlopen(base,timeout=2) as response:
                self.assertIn('data-demo="true"',response.read().decode())
            for name,mime in [('dashboard.css','text/css'),('dashboard.js','application/javascript'),('petcare-dog.webp','image/webp')]:
                with urllib.request.urlopen(base+'/assets/'+name,timeout=2) as response:
                    self.assertEqual(response.headers.get_content_type(),mime)
                    self.assertGreater(len(response.read()),100)
            for path in ['/assets/../servidor/dashboard.py','/assets/%2e%2e/dashboard.py','/assets/unknown.txt']:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(base+path,timeout=2)
                self.assertEqual(error.exception.code,404)
        finally:
            server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
