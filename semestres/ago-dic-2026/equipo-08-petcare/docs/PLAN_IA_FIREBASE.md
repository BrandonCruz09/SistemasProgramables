# Integración acordada: detección de perros y Firebase sin facturación

Plan inicial del 2 de noviembre de 2026, conservado como antecedente. **Actualización posterior:** el streaming, detector de perros/personas y página móvil ya se implementaron. Consulta [Video y detección](VIDEO_Y_DETECCION.md) para el estado vigente. Firebase y el circuito IA→actuador continúan pendientes.

## Alcance confirmado

Detectar **cualquier perro frente a los platos**. No reconocer a un perro individual, su raza, su identidad ni su estado de salud.

El material de clase «Sist Progr Unidad4 Firebase.pdf» (páginas 1, 3, 15–16 y 25) explica **Realtime Database**, plan **Spark**, y acceso mediante REST o `ufirebase.py`. Por tanto, Realtime Database es congruente con ese material; no hace falta migrar a Firestore para cumplir ese tema.

## Flujo previsto

1. La ESP32-CAM captura un JPEG y lo entrega mediante `/foto` en la red local.
2. Python en la PC descarga la imagen; OpenCV la decodifica.
3. Un modelo preentrenado de detección de objetos, ejecutado localmente con `cv2.dnn`, identifica la clase `dog` y devuelve cuadro delimitador y puntuación.
4. Se comprueba que el perro esté en una región definida frente a los platos. La cámara debe encuadrar parte suficiente del perro, no únicamente el interior de un plato.
5. Se exige presencia en varias capturas consecutivas para reducir avisos aislados. Los umbrales, número de capturas y latencia deben medirse con el montaje real.
6. La PC publica el resultado por MQTT y registra datos pequeños en Firebase. La ESP32 maneja los actuadores con sus bloqueos locales.

Modelo candidato: **MobileNet-SSD** preentrenado sobre VOC, compatible con OpenCV DNN. No es un detector de rostros. Antes de integrarlo se descargarán pesos desde la fuente original, se conservará licencia/procedencia y se probará con escenas con perro y sin perro. No se promete precisión a partir del valor de confianza del modelo.

Primera acción física propuesta para validar el circuito IA→MQTT→actuador: indicador LED de perro presente. El dispensado autónomo requiere después horario/ración, periodo de espera entre servicios, peso válido, límites y pruebas. Detectar repetidamente al perro **no debe abrir repetidamente la compuerta**. Ni esta acción LED por visión ni el dispensado autónomo están implementados en este avance.

## Firebase: presupuesto cero

- Mantener el proyecto en **Spark**, sin cuenta de facturación vinculada ni cambio a Blaze.
- Procesar IA en la PC; no usar una API de IA cobrada.
- Guardar peso, temperatura, nivel, estado y resultado de detección como JSON; no guardar secuencias de fotos en la base.
- Mantener las fotos en la red local; no depender de Cloud Storage ni Cloud Functions.
- Publicar con intervalo limitado y, para eventos de presencia, preferir cambios de estado. Definir retención del historial antes de dejarlo funcionando permanentemente.
- Configurar autenticación y reglas por usuarios autorizados. No publicar credenciales ni dejar lectura/escritura abierta al público.
- Revisar el consumo en la consola. El plan gratuito tiene límites; no significa uso ilimitado. La cuenta Firebase concreta todavía no se ha inspeccionado en esta sesión.

Datos previstos para visión: `dog_detected`, `confidence`, `bbox`, `in_bowl_zone`, `processed_at` y estado de disponibilidad de cámara/modelo. Un error de cámara debe indicar dato no disponible, no un falso «no hay perro».

## Utilidad de los archivos de clase ofrecidos

| Archivo o material | Uso en PetCare | Estado |
|---|---|---|
| Datasheet OV2640 | Consultar sensor, formatos y restricciones | Ofrecido; archivo exacto no revisado |
| Modificación HACA de base programadora | Referencia de alimentación/programación si corresponde a esa placa | Ofrecido; no aplicar una modificación física sin revisar documento/modelo |
| `uFirebase.py` | Alternativa de acceso Firebase desde MicroPython | Ofrecido; no localizado. No es obligatorio para el puente PC existente |
| Ver cámara web | Posible reutilización de captura/visualización de JPEG | Ofrecido; archivo exacto no revisado |
| Detección de rostros SRN / face detector | Posible referencia de lectura de imágenes e inferencia | Ofrecidos; si detectan rostros humanos, no detectan perros directamente |
| PDF Unidad 4 Firebase | Confirma RTDB/Spark y dos rutas REST/ufirebase | Revisadas páginas relevantes |

Los ejemplos de detección y `ufirebase.py` no se encontraron por nombre en Descargas, Escritorio ni la carpeta del proyecto. Se deben aportar los archivos exactos antes de afirmar compatibilidad o copiarlos al firmware.

## Estado actual frente al objetivo

**Actual:** cámara con enlace local reportado funcionando; tres JPEG comprobados sin Wi-Fi; puente PC con diferencia entre cuadros, MQTT y cliente RTDB en código; pruebas de lógica en PC.

**Pendiente:** integrar y probar modelo de perros, región de platos, estabilización temporal, resultado MQTT→actuador, autenticación/reglas Firebase y prueba integral. Las imágenes por MQTT que pide el esquema general del curso siguen pendientes: el transporte actual de imágenes es HTTP.

## Fuentes técnicas

- Plan Spark y condiciones: https://firebase.google.com/pricing
- Planes Firebase: https://firebase.google.com/docs/projects/billing/firebase-pricing-plans
- OpenCV DNN: https://opencv.org/opencv4-dnn-module/
- Modelo candidato y licencia original: https://github.com/chuanqi305/MobileNet-SSD

## Siguiente prueba medible

Con la cámara fija, registrar escenas con perro y sin perro, incluir personas cruzando y cambios de luz. Medir aciertos, falsos avisos y demora desde captura hasta indicador; anotar configuración y resultados reales. No asignar porcentajes ni segundos como resultados hasta medirlos.
