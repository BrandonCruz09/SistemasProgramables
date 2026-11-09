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
import time
import unittest
import urllib.request
from pathlib import Path
from dashboard import DashboardState, start_dashboard
from unittest.mock import patch


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


if __name__=='__main__':unittest.main()
