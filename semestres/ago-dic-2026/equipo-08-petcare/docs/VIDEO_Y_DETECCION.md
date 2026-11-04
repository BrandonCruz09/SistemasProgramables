# Video y detección de PetCare

Avance del 2 de noviembre de 2026. Equipo 08.

Actualización del 3 de noviembre: MQTT y Firebase ya se probaron con una ESP32 simulada y datos ficticios. Ver [Firebase y simulación](FIREBASE_Y_SIMULACION.md). Los pendientes y observaciones de esta página corresponden a la prueba original de video; la integración con sensores reales sigue pendiente.

La ESP32-CAM ya transmite video a la computadora. La PC ejecuta MobileNet SSD con OpenCV, dibuja los recuadros y comparte el resultado en una página que se puede abrir desde el celular. En la prueba del equipo se confirmó video en el teléfono y detección de una persona y de un perro. También se observó una confusión: en algunos momentos el perro fue marcado como persona.

## Cómo funciona

La cámara conserva la resolución VGA de 640 × 480 y calidad JPEG 12. La ruta `/stream` entrega una secuencia MJPEG; `/foto` conserva la captura individual. Solo se permite un flujo de video desde la placa. La PC mantiene esa conexión y distribuye el resultado a los navegadores. Así, abrir un segundo visor no crea otra transmisión en la ESP32-CAM.

La recepción y la detección usan hilos distintos. Solo se conserva el cuadro más reciente, para no formar una fila de imágenes atrasadas. No se graba video ni se suben imágenes a Firebase. Si pasan más de cuatro segundos sin una imagen reciente, la página muestra falta de señal y las detecciones pasan a estado desconocido.

El modelo identifica las clases `dog` y `person` de VOC. Es un modelo preentrenado; no se entrenó con imágenes del equipo. Se ejecuta en CPU, sin API de pago. Cada imagen se ajusta a 300 × 300 para la inferencia. Se conserva el preprocesamiento de su autor: BGR, media 127.5 y escala 0.007843.

## Ajuste después de la prueba con el perro

El integrante confirmó que el perro estaba solo cuando apareció la etiqueta Persona. Se registró como falso positivo. Se establecieron mínimos separados: perro 0.60 y persona 0.80. La presencia debe repetirse en tres cuadros procesados consecutivos. Antes de confirmarse, el recuadro lleva `?`.

Cuando dos clases ocupan casi el mismo recuadro (IoU mayor que 0.75), se compara su puntuación. Si la diferencia es menor que 0.15, ambas se consideran dudosas y no confirman presencia. Si la diferencia es mayor, se conserva la de mayor puntuación. Esto no corrige los casos donde el modelo solo devuelve una clase equivocada. Falta medir falsos positivos y omisiones con una cámara fija, iluminación estable y el montaje final.

Las puntuaciones no son un porcentaje de precisión del proyecto. Subir el mínimo puede reducir avisos falsos y también perder detecciones. No se calculó una matriz de confusión ni una tasa de aciertos en esta sesión.

## Archivos principales

| Archivo | Trabajo que realiza |
|---|---|
| `firmware/esp32cam/main.py` | Espera tres segundos y arranca la cámara al energizar. |
| `firmware/esp32cam/camara_wifi.py` | Wi-Fi, captura, HTTP y MJPEG con cierre de conexiones. |
| `servidor/video_source.py` | Recibe JPEG, limita el tamaño y reconecta si se corta el flujo. |
| `servidor/detector.py` | Carga el modelo, filtra clases y confirma presencia. |
| `servidor/video_web.py` | Sirve la página, el video procesado y el estado JSON. |
| `servidor/vision_main.py` | Coordina recepción, inferencia y servidor web. |
| `interfaz/index.html` | Vista adaptable al celular, pausa, reconexión y captura. |
| `servidor/descargar_modelo.py` | Descarga los archivos originales y comprueba SHA-256. |
| `servidor/petcare_server.py` | Consulta `/api/status` y puede publicar resultados en MQTT/Firebase. |

## Instalación en la cámara

1. Conectar la ESP32-CAM mediante la base ESP32CAM-MB. Se conserva MicroPython con soporte de `camera`; el firmware genérico no incluye necesariamente ese módulo.
2. En Thonny seleccionar MicroPython ESP32 y el puerto detectado. En esta prueba fue COM9; puede cambiar.
3. Completar `wifi_config.py` a partir del ejemplo y guardar `wifi_config.py`, `camara_wifi.py` y `main.py` en la placa.
4. Reiniciar. La consola imprime su IP. Abrir `/foto` para comprobar una imagen o `/stream` para ver video sin detecciones.
5. Cerrar el visor directo de `/stream` antes de iniciar la PC. La placa admite un flujo; la página de la PC distribuye el video a varios visores.

Los tres archivos quedaron cargados en la placa durante esta sesión. Se respaldó `boot.py`, el único archivo presente antes de cargar el avance. Se comprobó el arranque desde `main.py` después de un reinicio. El respaldo y las claves se mantienen fuera de Git.

## Instalación en la PC

Desde `servidor/`, con Python 3.10 o posterior:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe descargar_modelo.py
```

Copiar `server_config.example.json` como `server_config.json`. Ajustar `camera_stream_url` a `http://IP_DE_LA_CAMARA/stream`. Dejar Firebase desactivado hasta configurar la cuenta y sus reglas. Para esta etapa no hace falta iniciar Mosquitto.

Ejecutar `iniciar_video.cmd` o:

```powershell
.venv\Scripts\python.exe vision_main.py
```

La consola indica `http://IP_DE_LA_PC:8765/`. Abrir esa dirección en el celular conectado a la misma red Wi-Fi. Se usa la IP de la PC para ver las detecciones, no la IP de la cámara. El servidor admite hasta cuatro transmisiones a navegadores. El acceso está pensado para la red local; no se configuró acceso desde Internet.

Para cerrar, usar Ctrl+C en la consola del servidor o `detener_video.cmd`. El botón Pausar vista solo detiene la imagen de ese navegador; no apaga la cámara ni detiene la IA de la PC. La carpeta de accesos del escritorio es local y no se incluye en Git.

## Conexión con MQTT y Firebase

El puente existente usa `vision_url`, que apunta a `http://127.0.0.1:8765/api/status`, para no abrir otro flujo en la cámara. Publica `available`, `dog_detected`, `person_detected`, `dog_in_bowl_zone`, recuadros y tiempos. Se mantiene el tópico `petcare/equipo8/vision`. Si no hay datos recientes, las detecciones son `null`, no un falso "no hay perro".

En esta sesión no había broker en el puerto local 1883. La publicación MQTT/Firebase quedó preparada en código y probada con dobles, no validada con servicios reales. No se envían órdenes de alimento desde la detección.

## Zona de platos

`bowl_zone` permanece en `null`, porque la cámara todavía no está instalada en la carcasa. Al fijarla se puede usar `[x1, y1, x2, y2]`, con coordenadas entre 0 y 1. Se comprueba si el centro del recuadro del perro cae dentro de esa región. Es una aproximación de posición: no demuestra que esté comiendo o tomando agua.

## Resultados y pendientes

- Dos conexiones directas entregaron 15 JPEG válidos cada una, a 640 × 480. Los tiempos fueron 5.47 s y 7.78 s, equivalentes a 2.74 y 1.93 cuadros/s contando la apertura de conexión.
- En una muestra posterior de diez consultas a la PC hubo imagen disponible en todas; se observaron 2.35 cuadros/s de media y 70.4 ms de inferencia media. Son muestras breves, no una garantía de rendimiento.
- El usuario confirmó video móvil, detección de persona y detección de perro. Reportó también perro confundido con persona.
- Se comprobó que al detener la cámara se muestra falta de señal y que el servidor recupera el video cuando vuelve. Se corrigió un puerto HTTP que quedaba ocupado al reiniciar.
- La placa mostró un brownout en el arranque inicial; después logró transmitir por la conexión USB que funcionaba. No se desactivó la protección. Falta validar estabilidad prolongada y alimentación final.
- Pendientes: medir la confusión perro/persona con los nuevos filtros, fijar zona de platos, validar MQTT/Firebase, probar sensores y actuadores con el montaje final.

## Materiales consultados

El visor de clase usa `cv2.VideoCapture` con una URL `/video`; le falta importar `time` para su reconexión. El detector de rostros abre la webcam de la PC y necesita `deploy.prototxt` y pesos ResNet-10. Sirvió como referencia de la secuencia imagen → red → recuadros, pero ese modelo no detecta perros.

`ufirebase.py` se revisó como alternativa de MicroPython: el archivo proporcionado no incluye autenticación ni tiempos de espera de sockets y descarta algunas respuestas HTTP. Por ahora se conserva el puente REST de la PC. El datasheet OV2640 confirma video y captura individual, sin garantizar la velocidad por Wi-Fi de este montaje.

- Modelo, preprocesamiento y licencia: https://github.com/chuanqi305/MobileNet-SSD
- OpenCV DNN: https://docs.opencv.org/4.x/d6/d0f/group__dnn.html
- Firebase REST: https://firebase.google.com/docs/database/rest/auth

El origen exacto y las huellas del modelo están en `servidor/models/manifest.json`. Los pesos se descargan por separado; no se suben al repositorio del curso. Se conserva la licencia MIT del autor.
