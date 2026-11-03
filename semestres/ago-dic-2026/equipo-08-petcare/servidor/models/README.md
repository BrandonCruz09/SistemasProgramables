# Modelo de detección

MobileNet SSD preentrenado sobre VOC por chuanqi305. Se usan las clases dog (12) y person (15); no se entrenó un modelo propio.

Ejecutar `python descargar_modelo.py` desde servidor. `manifest.json` fija la revisión, tamaño y SHA-256 de los archivos originales. El script verifica cada descarga. Los pesos y el prototxt quedan excluidos de Git; la licencia MIT se conserva en LICENSE.

Fuente: https://github.com/chuanqi305/MobileNet-SSD/tree/bb17b6c3eef36d80be441ae8e5339be66e8e3b7a
