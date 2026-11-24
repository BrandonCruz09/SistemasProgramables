# Tabla HAL de PetCare

## Objetivo del proyecto

Desarrollar un dispensador supervisado para perro que registre el peso del alimento, permita accionar una compuerta y una bomba de agua desde una página web, e integre sensores y una cámara con procesamiento de visión en una PC. La aplicación usa MQTT para comunicar la placa con el servidor y Cloud Firestore para conservar lecturas y eventos.

## Estado y asignación de pines

Esta tabla describe la versión de firmware `petcare-23nov-r9`. Los pines son la configuración del programa; la telemetría más reciente que había disponible es histórica y no certifica el cableado ni el estado físico del día de la presentación.

| Módulo | ESP32 DevKit | Función y datos | Condición documentada |
|---|---:|---|---|
| Celda de carga y HX711 | DT 19, SCK 18 | Peso en gramos, RAW, estado y antigüedad de lectura | Factor y tara guardados; factor requiere validación con masa medida independientemente |
| DHT22 | DATA 4 | Temperatura °C y humedad relativa % | Hubo lecturas fallidas en registros previos; revisar en el montaje actual |
| PIR | OUT 27 | Estado lógico de movimiento | El nivel de salida depende de la placa del sensor; no exceder 3.3 V en GPIO |
| MG995 | PWM 33 | Apertura, cierre y posición intermedia desde el panel | 50 Hz; pulsos limitados a 850 µs abierto y 1500 µs cerrado |
| Módulo de relevador HW-383, canal K1 | IN1 23 | Control de la bomba, activo en nivel bajo | Pulso de agua limitado a 5000 ms; confirmar que el corte físico ocurra |
| Buzzer pasivo de tres terminales | S 22; VCC/GND según módulo | Avisos al mover compuerta, ordenar agua y prueba manual | Confirmar sonido en montaje; una confirmación de software no verifica sonido físico |
| OLED SSD1306, si se instala | SDA 26, SCL 25 | Mostrar peso local | La documentación no confirma una prueba física reciente del display |
| ESP32-CAM con OV2640 | Bus interno de cámara | Captura de JPEG; HTTP hacia la PC | Cámara separada; no se conecta por UART a la DevKit |

## Protocolo y datos

Prefijo MQTT: `petcare/equipo8`. Los mensajes de control se validan con acción permitida, identificador y sesión de la placa. Las credenciales del broker permanecen en archivos locales ignorados por Git.

| Tópico | Emisor → receptor | Contenido |
|---|---|---|
| `petcare/equipo8/telemetry` | ESP32 → servidor Python | Peso, sensores, estado de control y límites configurados |
| `petcare/equipo8/commands` | Panel/servidor → ESP32 | `feed`, `water`, `stop_water`, `gate_open`, `gate_close`, `gate_position`, `tone`, `auto_enable`, `auto_disable` |
| `petcare/equipo8/ack` | ESP32 → servidor Python | Resultado lógico de la orden e identificador relacionado |
| `petcare/equipo8/cam/frame` | ESP32-CAM → servidor, solo si se selecciona transporte MQTT | JPEG binario; la configuración actual usa HTTP |
| `petcare/equipo8/vision` | Procesamiento en PC → ESP32/servidor | Clasificación, confianza, tiempo y señal de presencia |

El servidor de PC utiliza la API REST de Cloud Firestore bajo `petcare/equipo8`. Guarda estado reciente e histórico de lecturas y eventos. Las pruebas de noviembre incluyen escritura y lectura reales en Firestore. Un resultado con `simulated: true` corresponde a una prueba simulada, no a una medición física.

## Límites de control

- El deslizador del panel convierte 0–100 % a pulsos entre 1500 y 850 µs. El firmware vuelve a validar el intervalo antes de mover el MG995.
- El servido manual de alimento se supervisa con el HX711 y termina al alcanzar 300 g totales, al vencer el tiempo o cuando la lectura deja de ser válida. La exactitud depende de validar el factor con una masa conocida.
- El agua se activa durante un máximo de 5 s por orden. El sistema no mide el volumen ni el nivel del depósito.
- El modo automático se arma manualmente desde el panel y queda desarmado al reiniciar. La detección puede fallar y necesita verificación con el perro y el encuadre definitivos.
- ACK confirma que el programa aceptó o aplicó una orden a nivel lógico; no comprueba por sí solo que el servo se movió, el relevador conmutó o el agua dejó de fluir.

## Alimentación y referencia de conexión

DevKit por USB durante la carga; HX711 y sensores compatibles a 3.3 V. El MG995 y la bomba usan alimentación externa de 5 V con capacidad suficiente. Conectar el borne de salida V− de la fuente a GND común de la DevKit y a los retornos de baja tensión. El símbolo de tierra de protección `⏚` no sustituye a V− y no va al riel negativo del protoboard. No unir la salida V+ externa con VIN/5V mientras la placa esté alimentada por USB, salvo que el diseño de la placa y la alimentación estén aislados y verificados.

El protoboard se usa para señales y distribución de baja corriente; no llevar por sus contactos la corriente del MG995 o la bomba. La línea de agua debe mantenerse físicamente separada de la electrónica y de la fuente. Consulta [montaje y conexiones](MONTAJE_Y_CONEXIONES.md) y la versión actual de [arquitectura](arquitectura.png) y [cableado](diagrama.png).
