# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: test_vision.py
# Objetivo: Comprobar recepcion de video, filtrado y estado sin datos recientes.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; pruebas en PC.
# ============================================
import json
import threading
import time
import unittest
from pathlib import Path
import numpy as np
import requests
from detector import PresenceFilter, decode_detections, resolve_overlaps
from video_source import jpeg_frames
from video_web import VideoState, create_server
from petcare_server import PetCareBridge


class VisionTests(unittest.TestCase):
    def test_person_uses_a_higher_threshold(self):
        rows = np.array([[0,15,.76,0,0,.5,.5], [0,12,.76,.5,.5,1,1]])
        result = decode_detections(rows, 640, 480, .55, {'person':.80, 'dog':.60})
        self.assertEqual([d['class'] for d in result], ['dog'])

    def test_conflicting_classes_are_not_counted_twice(self):
        dog = {'class':'dog', 'confidence':.89, 'bbox':[0,0,100,100]}
        person = {'class':'person', 'confidence':.86, 'bbox':[0,0,100,100]}
        kept, unsure = resolve_overlaps([dog,person])
        self.assertEqual(kept, [])
        self.assertEqual(len(unsure), 2)
        person['bbox'] = [200,0,300,100]
        self.assertEqual(len(resolve_overlaps([dog,person])[0]), 2)

    def test_jpeg_split_across_packets(self):
        chunks = [b'header\xff', b'\xd8abc\xff', b'\xd9\r\n\xff\xd8def', b'\xff\xd9']
        self.assertEqual(list(jpeg_frames(chunks)), [b'\xff\xd8abc\xff\xd9', b'\xff\xd8def\xff\xd9'])

    def test_incomplete_and_oversized_frame(self):
        self.assertEqual(list(jpeg_frames([b'header only', b'\xff\xd8incomplete'])), [])
        with self.assertRaises(ValueError):
            list(jpeg_frames([b'\xff\xd8' + b'x'*100], limit=20))

    def test_classes_threshold_and_clipping(self):
        rows = np.array([[0, 12, .9, -.1, .1, 1.1, .8],
                         [0, 15, .4, .1, .1, .5, .5],
                         [0, 7, .99, 0, 0, 1, 1],
                         [0, 15, .8, .5, .5, .8, .9],
                         [0, 12, float('nan'), 0, 0, 1, 1]])
        found = decode_detections(rows, 640, 480, .55)
        self.assertEqual([r['class'] for r in found], ['dog', 'person'])
        self.assertEqual(found[0]['bbox'], [0, 48, 639, 384])

    def test_confirmation_requires_consecutive_frames(self):
        filt = PresenceFilter(3)
        dog = [{'class': 'dog', 'in_bowl_zone': True}]
        self.assertFalse(filt.update(dog)['dog'])
        self.assertFalse(filt.update(dog)['dog'])
        self.assertTrue(filt.update(dog)['dog_in_zone'])
        self.assertFalse(filt.update([])['dog'])
        filt.update(dog)
        filt.reset()
        self.assertFalse(filt.update(dog)['dog'])

    def test_stale_frame_does_not_report_absence_or_keep_positive(self):
        state = VideoState(stale_seconds=1)
        state.update(b'jpeg', {'available': True, 'dog_detected': True}, time.monotonic()-2)
        _, jpeg, status = state.snapshot()
        self.assertFalse(status['available'])
        self.assertIsNone(status['dog_detected'])
        self.assertEqual(jpeg, state.waiting)

    def test_bridge_marks_vision_unavailable_on_network_error(self):
        bridge = PetCareBridge({'vision_url': 'http://127.0.0.1/api/status'})
        class Broken:
            def get(self, *args, **kwargs):
                raise OSError('offline')
        bridge.requests = Broken()
        bridge.poll_vision()
        self.assertEqual(bridge.last_motion_state, (False, None, None, None))

    def test_http_page_status_and_two_readers(self):
        state = VideoState()
        server = create_server(state, '127.0.0.1', 0, Path(__file__).resolve().parents[1]/'interfaz/index.html')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:%d' % server.server_port
        session = requests.Session()
        session.trust_env = False
        try:
            self.assertIn('PetCare', session.get(base, timeout=2).text)
            self.assertFalse(session.get(base+'/api/status', timeout=2).json()['available'])
            for _ in range(2):
                with session.get(base+'/stream', stream=True, timeout=2) as r:
                    self.assertIn('multipart/', r.headers['Content-Type'])
                    frame = next(jpeg_frames(r.iter_content(512)))
                    self.assertTrue(frame.startswith(b'\xff\xd8'))
            self.assertEqual(session.get(base+'/missing', timeout=2).status_code, 404)
        finally:
            server.stopping.set()
            with state.condition:
                state.condition.notify_all()
            server.shutdown()
            server.server_close()
            thread.join(2)
            session.close()


if __name__ == '__main__':
    unittest.main()
