# Sistemas Programables - PetCare, Equipo 08
# Brandon Leonel Padilla De la Cruz, Isaac Eliseo Flores Valencia,
# Lidia Verenice Padilla Lopez. Pines: no aplica, PC.
# Registro local persistente y reintento de eventos de agua en Firestore.
import json
import re
import sqlite3
import time


class WaterLog:
    def __init__(self, path=':memory:'):
        self.db = sqlite3.connect(str(path))
        self.db.execute('CREATE TABLE IF NOT EXISTS water (path TEXT PRIMARY KEY, payload TEXT, sent INTEGER DEFAULT 0)')
        self.db.commit()
        self.retry_at = 0

    def add(self, root, payload):
        event_id = payload.get('id', '')
        if not isinstance(event_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', event_id):
            return False
        if payload.get('phase') not in ('started', 'finished'):
            return False
        cursor = self.db.execute('INSERT OR IGNORE INTO water(path,payload) VALUES (?,?)',
                                (root+'/eventos_agua/'+event_id, json.dumps(payload, allow_nan=False)))
        self.db.commit()
        return cursor.rowcount > 0

    def flush(self, cloud):
        if cloud is None or time.monotonic() < self.retry_at:
            return
        row = self.db.execute('SELECT path,payload FROM water WHERE sent=0 ORDER BY rowid LIMIT 1').fetchone()
        if row is None:
            return
        try:
            cloud.put(row[0], json.loads(row[1]))
        except Exception:
            self.retry_at = time.monotonic()+60
            return
        self.db.execute('UPDATE water SET sent=1 WHERE path=?', (row[0],))
        self.db.commit()

    def summary(self):
        total, pending = self.db.execute('SELECT COUNT(*),COALESCE(SUM(1-sent),0) FROM water').fetchone()
        return {'total_events': total, 'pending_cloud': pending}

    def close(self):
        self.db.close()
