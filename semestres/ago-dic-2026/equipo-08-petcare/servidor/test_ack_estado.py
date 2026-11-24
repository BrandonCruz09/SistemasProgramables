# Proyecto: PetCare, equipo 08.
# Integrantes: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312).
# Objetivo: Comprobar mediante pruebas de software el módulo ack estado de PetCare.

import unittest
from dashboard import DashboardState

class AckTests(unittest.TestCase):
    def test_ack_replaces_pending_instead_of_duplicate(self):
        s=DashboardState()
        s.command_sent('a','beep','ahora')
        s.command_ack({'id':'a','ok':True,'message':'Senal enviada'},'despues')
        self.assertEqual(len(s.events),1)
        self.assertFalse(s.events[0]['pending'])
        self.assertEqual(s.events[0]['message'],'Senal enviada')

    def test_timeout_is_unknown_and_late_ack_updates(self):
        s=DashboardState();s.command_sent('a','water','ahora')
        s.events[0]['sent_monotonic']-=11
        s.expire_commands()
        self.assertIn('desconocido',s.events[0]['message'])
        s.command_ack({'id':'a','ok':False,'message':'Rechazado'},'despues')
        self.assertEqual(len(s.events),1)
        self.assertFalse(s.events[0]['ok'])

if __name__=='__main__':unittest.main()
