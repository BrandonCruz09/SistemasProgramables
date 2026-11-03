# ============================================
# Proyecto: PetCare — Equipo 08
# Archivo: detector.py
# Objetivo: Detectar perros y personas con MobileNet SSD en la PC.
# Equipo: Brandon Leonel Padilla De la Cruz (22240293); Isaac Eliseo Flores Valencia (22240324); Lidia Verenice Padilla López (22240312)
# Materia: Sistemas Programables — ISC TecNM León
# Semestre: ago-dic-2026
# Pines: No aplica; procesamiento en PC.
# ============================================
import time
from pathlib import Path
import cv2
import numpy as np

CLASSES = {12: ('dog', 'Perro'), 15: ('person', 'Persona')}


def decode_detections(output, width, height, threshold, class_thresholds=None):
    detections = []
    for row in output.reshape(-1, 7):
        if not np.isfinite(row).all():
            continue
        class_id, score = int(row[1]), float(row[2])
        if class_id not in CLASSES:
            continue
        name, label = CLASSES[class_id]
        minimum = (class_thresholds or {}).get(name, threshold)
        if score < minimum:
            continue
        box = row[3:7] * [width, height, width, height]
        x1, y1, x2, y2 = [int(v) for v in box]
        x1, x2 = max(0, x1), min(width - 1, x2)
        y1, y2 = max(0, y1), min(height - 1, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        detections.append({'class': name, 'label': label,
                           'confidence': round(score, 4), 'bbox': [x1, y1, x2, y2]})
    return detections


def resolve_overlaps(detections):
    discarded, uncertain = set(), set()
    for i, a in enumerate(detections):
        for j in range(i+1, len(detections)):
            b = detections[j]
            if a['class'] == b['class']:
                continue
            x1, y1, x2, y2 = a['bbox']
            u1, v1, u2, v2 = b['bbox']
            intersection = max(0, min(x2,u2)-max(x1,u1)) * max(0, min(y2,v2)-max(y1,v1))
            union = (x2-x1)*(y2-y1) + (u2-u1)*(v2-v1) - intersection
            if union and intersection / union > .75:
                # Dos clases sobre casi el mismo objeto necesitan mayor separacion.
                if abs(a['confidence']-b['confidence']) < .15:
                    uncertain.update((i,j))
                else:
                    discarded.add(i if a['confidence'] < b['confidence'] else j)
    return ([d for i,d in enumerate(detections) if i not in discarded | uncertain],
            [d for i,d in enumerate(detections) if i in uncertain])


class PresenceFilter:
    def __init__(self, frames=3):
        self.frames = max(1, int(frames))
        self.reset()

    def reset(self):
        self.counts = {'dog': 0, 'person': 0, 'dog_in_zone': 0}

    def update(self, detections):
        present = {d['class'] for d in detections}
        dog_in_zone = any(d['class'] == 'dog' and d.get('in_bowl_zone') for d in detections)
        for key in self.counts:
            found = dog_in_zone if key == 'dog_in_zone' else key in present
            self.counts[key] = min(self.frames, self.counts[key] + 1) if found else 0
        return {key: count >= self.frames for key, count in self.counts.items()}


class DogPersonDetector:
    def __init__(self, model_dir, threshold=.55, confirm_frames=3, bowl_zone=None, class_thresholds=None):
        folder = Path(model_dir)
        proto = folder / 'deploy.prototxt'
        weights = folder / 'mobilenet_iter_73000.caffemodel'
        if not proto.exists() or not weights.exists():
            raise FileNotFoundError('Falta el modelo. Ejecuta: python descargar_modelo.py')
        self.net = cv2.dnn.readNetFromCaffe(str(proto), str(weights))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.threshold = float(threshold)
        if not 0 < self.threshold < 1:
            raise ValueError('confidence debe estar entre 0 y 1')
        self.presence = PresenceFilter(confirm_frames)
        self.class_thresholds = class_thresholds or {'dog': .60, 'person': .80}
        if any(not 0 < float(v) < 1 for v in self.class_thresholds.values()):
            raise ValueError('Los umbrales por clase deben estar entre 0 y 1')
        self.zone = bowl_zone
        if self.zone is not None:
            if (len(self.zone) != 4 or not all(0 <= v <= 1 for v in self.zone)
                    or self.zone[0] >= self.zone[2] or self.zone[1] >= self.zone[3]):
                raise ValueError('bowl_zone: [x1,y1,x2,y2] normalizados entre 0 y 1')

    def analyze(self, frame):
        start = time.monotonic()
        h, w = frame.shape[:2]
        # El modelo VOC usa BGR, media 127.5 y escala 0.007843.
        blob = cv2.dnn.blobFromImage(frame, .007843, (300, 300), 127.5, swapRB=False)
        self.net.setInput(blob)
        detections = decode_detections(self.net.forward(), w, h, self.threshold, self.class_thresholds)
        detections, uncertain = resolve_overlaps(detections)
        for d in detections:
            x1, y1, x2, y2 = d['bbox']
            cx, cy = (x1 + x2) / (2 * w), (y1 + y2) / (2 * h)
            d['in_bowl_zone'] = bool(self.zone and self.zone[0] <= cx <= self.zone[2]
                                     and self.zone[1] <= cy <= self.zone[3])
        stable = self.presence.update(detections)
        annotated = frame.copy()
        if self.zone:
            a, b, c, e = self.zone
            cv2.rectangle(annotated, (int(a*w), int(b*h)), (int(c*w), int(e*h)), (220, 180, 60), 1)
        for d in detections:
            x1, y1, x2, y2 = d['bbox']
            color = (60, 200, 80) if d['class'] == 'dog' else (230, 160, 60)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            suffix = '' if stable[d['class']] else ' ?'
            cv2.putText(annotated, '%s%s %.1f%%' % (d['label'], suffix, 100*d['confidence']),
                        (x1, max(18, y1-7)), cv2.FONT_HERSHEY_SIMPLEX, .55, color, 2)
        result = {'available': True, 'method': 'MobileNet-SSD VOC / OpenCV DNN',
                  'detections': detections, 'uncertain_detections': len(uncertain),
                  'dog_detected': stable['dog'],
                  'person_detected': stable['person'], 'dog_in_bowl_zone': stable['dog_in_zone'],
                  'zone_configured': self.zone is not None,
                  'inference_ms': round(1000 * (time.monotonic()-start), 1)}
        return annotated, result
