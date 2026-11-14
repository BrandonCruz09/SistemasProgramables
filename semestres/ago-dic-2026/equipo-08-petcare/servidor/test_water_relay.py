# Sistemas Programables - PetCare, Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez. Pines simulados: rele GPIO23.
# Objetivo: verificar servido manual, polaridad, duplicados y registro durable.
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import test_petcare
from water_log import WaterLog
from dashboard import DashboardState, start_dashboard
from petcare_server import PetCareBridge
from actuadores import PumpRelay
from mqtt_link import MQTTLink
import config


class WaterRelayTests(unittest.TestCase):
    def controller(self):
        factory = test_petcare.PetCareTests()
        c = factory.make_controller(calibrated=False, weight=None, water=None)
        c.tick(0)
        return c

    def test_no_float_unknown_level_and_single_pulse(self):
        c = self.controller()
        self.assertIsNone(c.snapshot()['water_available'])
        self.assertTrue(c.request_pump(0)[0])
        self.assertFalse(c.request_pump(200)[0])
        c.tick(14999); self.assertTrue(c.pump.active)
        c.tick(15000); self.assertFalse(c.pump.active)
        self.assertFalse(c.request_pump(24999)[0])
        self.assertTrue(c.request_pump(25000)[0])
        self.assertEqual([e['phase'] for e in c.water_events], ['started','finished','started'])
        self.assertTrue(all(e['volume_ml'] is None for e in c.water_events))

    def test_manual_stop_and_shutdown(self):
        c=self.controller();c.request_pump(0);c.stop_pump(500)
        self.assertFalse(c.pump.active)
        self.assertEqual(c.water_events[-1]['duration_ms'],500)
        c.request_pump(11000);c.safe_shutdown()
        self.assertFalse(c.pump.active)

    def test_pending_log_blocks_more_water_without_discard(self):
        c=self.controller();c.water_events=[{}]*31
        self.assertFalse(c.request_pump(0)[0]);self.assertFalse(c.pump.active)

    def test_relay_high_at_boot_and_timer_cuts_low_pulse(self):
        pin=Mock();timer=Mock()
        timer_cls=Mock(return_value=timer);timer_cls.ONE_SHOT=0
        factory=Mock(return_value=pin)
        with patch.dict(sys.modules,{'machine':types.SimpleNamespace(Pin=factory,Timer=timer_cls)}):
            pump=PumpRelay()
            self.assertEqual(factory.call_args.kwargs['value'],1)
            pump.on();self.assertEqual(pin.value.call_args.args,(0,))
            self.assertEqual(timer.init.call_args.kwargs['period'],15000)
            timer.init.call_args.kwargs['callback'](timer)
            self.assertEqual(pin.value.call_args.args,(1,));self.assertFalse(pump.active)
            timer.init.side_effect=RuntimeError('Timer no disponible')
            with self.assertRaises(RuntimeError):pump.on()
            self.assertEqual(pin.value.call_args.args,(1,))

    def test_mqtt_water_requires_current_session_and_supervision(self):
        c=self.controller();link=MQTTLink();link.client=Mock()
        link.pending_command={'id':'bad','action':'water'};link._run_command(c,0)
        self.assertFalse(c.pump.active)
        link.pending_command={'id':'good','action':'water','supervised':True,'session_id':c.snapshot()['session_id']}
        link._run_command(c,0);self.assertTrue(c.pump.active)
        c.stop_pump(10)
        link.pending_command={'id':'other','action':'stop_water'};link._run_command(c,20)
        link.pending_command={'id':'good','action':'water','supervised':True,'session_id':c.snapshot()['session_id']}
        link._run_command(c,20000);self.assertFalse(c.pump.active)

    def test_log_retry_dedup_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'log.sqlite3'
            log=WaterLog(path);event={'id':'run-started','phase':'started','volume_ml':None}
            self.assertTrue(log.add('petcare/equipo8',event))
            self.assertFalse(log.add('petcare/equipo8',event))
            cloud=Mock();cloud.put.side_effect=OSError()
            log.flush(cloud);self.assertEqual(log.summary()['pending_cloud'],1);log.close()
            log=WaterLog(path);cloud.put.side_effect=None;log.flush(cloud)
            self.assertEqual(log.summary()['pending_cloud'],0)
            self.assertEqual(cloud.put.call_args.args[0],'petcare/equipo8/eventos_agua/run-started')
            log.close()

    def test_dashboard_rejects_missing_confirmation_and_stale_device(self):
        state=DashboardState()
        self.assertFalse(state.request_command('water',True)[0])
        state.update({'status':{'state':'LISTO','session_id':'abc'}})
        self.assertFalse(state.request_command('water',False)[0])
        self.assertTrue(state.request_command('water',True)[0])
        self.assertEqual(state.commands.get()['session_id'],'abc')

    def test_http_button_token_and_command(self):
        import urllib.request
        import urllib.error
        state=DashboardState();state.update({'status':{'state':'LISTO','session_id':'abc'}})
        server=start_dashboard(state,Path(__file__).resolve().parents[1]/'interfaz/dashboard.html','127.0.0.1',0)
        try:
            url='http://127.0.0.1:'+str(server.server_port)
            self.assertIn('Prueba de agua 15 s',urllib.request.urlopen(url).read().decode())
            body=json.dumps({'action':'water','supervised':True}).encode()
            request=urllib.request.Request(url+'/api/command',data=body,headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(request)
            request.add_header('X-PetCare-Token',state.command_token)
            self.assertEqual(urllib.request.urlopen(request).status,202)
            self.assertEqual(state.commands.get()['action'],'water')
        finally:server.shutdown();server.server_close()

    def test_bridge_manual_water_never_retains_and_throttles(self):
        bridge=PetCareBridge({});client=Mock();client.is_connected.return_value=True;client.publish.return_value.rc=0
        bridge.set_mqtt_client(client);bridge.dashboard.update({'status':{'state':'LISTO','session_id':'abc'}})
        for _ in range(2):
            bridge.dashboard.request_command('water',True);bridge.process_manual_commands()
        client.publish.assert_called_once()
        payload=json.loads(client.publish.call_args.args[1])
        self.assertTrue(payload['supervised']);self.assertEqual(payload['session_id'],'abc')
        self.assertFalse(client.publish.call_args.kwargs['retain'])
        self.assertEqual(client.publish.call_args.kwargs['qos'],0)


if __name__=='__main__':unittest.main()
