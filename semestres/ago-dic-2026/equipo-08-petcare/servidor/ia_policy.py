# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: ia_policy.py
# Objetivo: Decidir una señal RGB por presencia reciente de perro.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; software en PC.
# ============================================
"""Una señal breve por presencia confirmada; nunca ordena comida ni agua."""
import math
import uuid


class DogSignalPolicy:
    def __init__(self, cooldown_seconds=15, absent_frames=3):
        self.cooldown = max(5, float(cooldown_seconds))
        self.absent_frames = max(1, int(absent_frames))
        self.armed = True
        self.absent = 0
        self.last_sent = float('-inf')
        self.last_frame = None

    def propose(self, result, now):
        if result.get('available') is not True:
            self.absent = 0
            return None
        age = result.get('frame_age_seconds')
        if not isinstance(age, (int, float)) or not math.isfinite(age) or not 0 <= age <= 3:
            self.absent = 0
            return None
        key = (result.get('processed_at'), result.get('frame_number'))
        if None in key or key == self.last_frame:
            return None
        self.last_frame = key
        if result.get('dog_detected') is False:
            self.absent += 1
            if self.absent >= self.absent_frames:
                self.armed = True
            return None
        self.absent = 0
        if result.get('dog_detected') is not True or not self.armed or now - self.last_sent < self.cooldown:
            return None
        dogs = [d for d in result.get('detections', []) if isinstance(d, dict) and d.get('class') == 'dog']
        confidence = max((d.get('confidence', 0) for d in dogs
                          if isinstance(d.get('confidence'), (int, float))
                          and math.isfinite(d['confidence']) and 0 <= d['confidence'] <= 1), default=0)
        if confidence < .60 or result.get('uncertain_detections', 0):
            return None
        return {'id': 'ia-' + uuid.uuid4().hex[:24], 'action': 'signal_dog',
                'source': 'vision', 'confidence': confidence,
                'frame_number': result['frame_number'], 'processed_at': result['processed_at']}

    def accepted(self, now):
        # Consumir la presencia solo cuando el cliente MQTT acepta el envío.
        self.armed = False
        self.last_sent = now
