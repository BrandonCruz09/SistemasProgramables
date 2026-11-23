# Tabla HAL — PetCare, equipo 08

Actualizada el 23 de noviembre de 2026 para corresponder al firmware r8 y al panel con deslizador de compuerta.

> El firmware y el panel describen el diseño de software. Las filas con estado físico pendiente requieren verificación en el montaje real.

Asignación del firmware de este avance. Son valores configurados, **no mediciones físicas** del montaje completo.
Prefijo MQTT: `petcare/equipo8`. El puerto USB de cada placa se selecciona en Thonny; no es un GPIO.

El 3 de noviembre se validó MQTT/Firebase con sensores y salidas simulados en PC, bajo el prefijo independiente `petcare/equipo8/simulacion/ID_EJECUCION`. Esa prueba no cambia los estados físicos de esta tabla ni calibra la celda.

| Componente | Tipo | Pin ESP32 principal | Publicación / campo | Suscripción / acción | Unidad o rango | Estado |
|---|---|---|---|---|---|---|
| Celda 5 kg + HX711 | Sensor | DT 19, SCK 18 | `/telemetry`: `status.weight_g`, `raw`, `hx_ok` | — | g; nominal 5000 g; tara −8994.451, factor 285.80386 | Calibración guardada; validar cambio de peso en la carcasa con una masa conocida |
| DHT22 | Sensor | DATA 4 | `/telemetry`: `temperature_c`, `humidity_pct`, `dht_ok` | — | °C y %HR; rango real por verificar | Sin respuesta en captura del 14 de noviembre; revisar conexión |
| PIR | Sensor | OUT 27 | `/telemetry`: `pir` | — | booleano | Confirmar modelo/VCC |
| Flotador retirado del alcance | — | Sin pin; GPIO26 ahora es SDA de OLED | `water_available=null`, `water_level_monitored=false` | — | Nivel no medido | No se instalará |
| MG995 | Actuador | PWM 33 | `/ack` y `status.state` | `/commands`: `feed`, `gate_open`, `gate_close`, `gate_position` | 850–1500 us; 50 Hz; posiciones intermedias desde el deslizador | Firmware r8 limita el recorrido y vigila peso/tiempo; validar sin forzar la compuerta |
| Bomba 3–5 V + relé HW-383 K1 | Actuador | IN1 23, activo LOW | `/ack`, `/water_events`, `status.state` | `/commands`: `water`, `stop_water` | máximo 5000 ms por pulso; sin volumen calibrado | Confirmar corte físico de agua en la presentación |
| LED RGB | — | Sin conexión | — | — | Eliminado del montaje | Fuera del alcance actual |
| OLED SSD1306 128×64 | Pantalla | SDA26 / SCL25, VCC3V3 | Peso local del mismo SensorHub | — | g, actualización nominal 800 ms | Preparada; pendiente conexión física |
| Buzzer pasivo | Actuador | 22 | ACK y estado auxiliar | `/commands`: `tone` | tonos PWM y avisos no bloqueantes | Comprobar en el montaje |
| ESP32-CAM OV2640 + MB | Cámara independiente | Bus interno; no TX/RX a DevKit | HTTP `/stream` → PC; puente consulta `/api/status` y publica `/vision` | GET `/foto` o `/stream` | JPEG VGA 640×480, calidad 12 | Streaming probado; detección móvil de perro/persona confirmada por el equipo |

Las órdenes MQTT usan JSON con `id` único, `action` y la sesión vigente del ESP32. Entre las acciones están `feed`, `water`, `stop_water`, `stop_food`, `gate_open`, `gate_close` y `gate_position` (esta última incluye `position_us`).

La comida usa el objetivo total de 300 g. El modo automático inicia desarmado y requiere activación expresa desde el panel. El cierre manual y automático se supervisa por peso, validez de la lectura y tiempo máximo. El agua funciona por pulsos de hasta 5 s; no mide volumen ni nivel. El reconocimiento de perro puede solicitar alimentación cuando el modo automático está armado.

La cámara independiente puede publicar frames por el transporte seleccionado en la configuración local. La PC ejecuta OpenCV/detector y sirve el visor y el panel. La detección no identifica perros individuales ni garantiza clasificación sin falsos positivos.

## Alimentación y montaje

- DevKit por USB durante pruebas. HX711 y DHT22 a 3V3/GND; señales del ESP32 a 3.3 V.
- MG995 rojo a +5 V externo, marrón/negro a V−, naranja/amarillo a GPIO33. V− unido a GND de DevKit; no unir V+ al VIN si DevKit está por USB.
- La base ESP32CAM-MB programa la cámara por USB. No se requiere FTDI.
- Confirmar VCC del PIR por modelo; no conectar una salida de 5 V directamente al ESP32.
- Bomba mediante COM1/NO1 del relé y diodo en paralelo con la bomba; nunca directo al GPIO. Ver guía del 11 de noviembre para RY-VCC y puente J1.
- Jarra azul: comida. Bote rojo: agua. Montaje propuesto con bomba, sin salida inferior abierta; confirmar que la bomba sea sumergible. El embudo abierto no detiene el flujo.
- Caja de coroplast con soportes rígidos para depósitos y celda; electrónica separada del agua.

## Comportamiento y límites

- El deslizador de compuerta traduce 0 % a la posición cerrada y 100 % al extremo abierto configurado. La placa solo acepta pulsos dentro de los extremos del firmware.
- La posición manual mantiene los cierres supervisados por peso, sensor y tiempo; el deslizador queda bloqueado durante la bomba y mientras corre un servido automático.
- Una lectura sin calibración o vencida bloquea la apertura/servido de alimento; no vuelve a tarar al arrancar.
- El relé apaga la bomba al terminar cada pulso de 5 s. Confirma el corte de flujo en el montaje, porque el firmware no mide físicamente el agua.
- El buzzer pasivo usa PWM y avisos no bloqueantes; una confirmación MQTT representa la orden aplicada por software, no una comprobación del sonido o movimiento físico.
- La automatización se desarma al reiniciar. Prueba primero cada actuador por separado y arma el modo automático solo después de verificar el montaje.
