# PetCare — Equipo 08 | Sistemas Programables
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293), Isaac Eliseo Flores
# Valencia (22240324), Lidia Verenice Padilla López (22240312).
# Objetivo: pruebas del formato, acceso y límites de Cloud Firestore.
# Pines: no aplica; pruebas de PC sin hardware.
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from firestore_rest import FirestoreREST, DailyBudget, encode, decode
from petcare_server import PetCareBridge


class FirestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.auth = Mock(id_token='token-de-prueba')
        self.db = FirestoreREST({'project_id':'petcare-equipo-08'}, self.temp.name, self.auth)
        response=Mock(ok=True,status_code=200,content=b'{}')
        response.json.return_value={}
        self.auth.session.request.return_value=response

    def test_types(self):
        data={'gramos':None,'temp':24.5,'pir':True,'frames':7,'labels':['dog'], 'nested':{'ok':False}}
        self.assertEqual(decode(encode(data)), data)

    def test_non_finite(self):
        for value in (float('inf'),float('nan')):
            with self.assertRaises(ValueError): encode(value)

    def test_document_mapping(self):
        self.assertEqual(self.db.document_path('petcare/equipo8/latest'),'petcare/equipo8/estado/latest')
        self.assertEqual(self.db.document_path('petcare/equipo8/lecturas/123'),'petcare/equipo8/lecturas/123')
        with self.assertRaises(ValueError): self.db.document_path('petcare/equipo8/lecturas')
        with self.assertRaises(ValueError): self.db.document_path('petcare/equipo8/../bad')

    def test_patch_preserves_other_fields(self):
        self.db.patch('petcare/equipo8/estado_actual',{'vision':{'dog':True}})
        args,kw=self.auth.session.request.call_args
        self.assertEqual(args[0],'PATCH')
        self.assertEqual(kw['params'],[('updateMask.fieldPaths','`vision`')])
        self.assertEqual(kw['headers']['Authorization'],'Bearer token-de-prueba')
        self.auth.session.request.assert_called_once()

    def test_budget_survives_restart(self):
        budget=DailyBudget(self.temp.name)
        budget.reserve('write',10000)
        with self.assertRaises(RuntimeError): DailyBudget(self.temp.name).reserve('write')

    def test_denied_is_not_empty_data(self):
        self.auth.session.request.return_value=Mock(ok=False,status_code=403)
        with self.assertRaisesRegex(RuntimeError,'403'): self.db.get('petcare/equipo8/latest')

    def test_missing_document_is_empty(self):
        response=Mock(ok=False,status_code=404)
        response.json.return_value={'error':{'message':'Document "projects/p/databases/(default)/documents/a/b" not found.'}}
        self.auth.session.request.return_value=response
        self.assertIsNone(self.db.get('petcare/equipo8/command'))

    def test_missing_database_is_error(self):
        response=Mock(ok=False,status_code=404)
        response.json.return_value={'error':{'message':'The database (default) does not exist.'}}
        self.auth.session.request.return_value=response
        with self.assertRaises(RuntimeError): self.db.get('petcare/equipo8/command')

    def test_quota_backoff(self):
        self.auth.session.request.return_value=Mock(ok=False,status_code=429)
        with self.assertRaises(RuntimeError): self.db.get('petcare/equipo8/latest')
        with self.assertRaisesRegex(RuntimeError,'espera'): self.db.get('petcare/equipo8/latest')
        self.auth.session.request.assert_called_once()

    def test_recent_is_bounded(self):
        self.db.recent('petcare/equipo8/lecturas')
        self.assertEqual(self.auth.session.request.call_args.kwargs['params']['pageSize'],120)
        self.assertEqual(json.loads((Path(self.temp.name)/'.firestore_budget.json').read_text())['read'],120)

    def test_cloud_throttle_keeps_local_current(self):
        cloud=Mock()
        bridge=PetCareBridge({'firebase':{'provider':'firestore'}},cloud)
        for i in range(20):
            bridge.messages.put(('petcare/equipo8/telemetry',{'status':{'state':'IDLE','last_event':str(i)}}))
        bridge.process_messages()
        self.assertEqual(cloud.put.call_count,2) # latest y lectura histórica
        self.assertEqual(cloud.patch.call_count,1)
        self.assertEqual(cloud.post.call_count,1)
        self.assertGreaterEqual(bridge.command_interval,30)


if __name__=='__main__': unittest.main()
