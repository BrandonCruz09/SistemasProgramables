# Tabla HAL — PetCare, equipo 08

> **Ampliación de software posterior a este corte:** ya se prepararon JPEG por MQTT, decisión IA con señal RGB, ACK, rutas de Firebase y dashboard. Pruebas de software y nube simulada aprobadas; carga y prueba física pendientes. [Estado actualizado y pasos](../docs/INTEGRACION_MQTT_IA.md).

Asignación del firmware de este avance. Son valores configurados, **no mediciones físicas** del montaje completo.
Prefijo MQTT: `petcare/equipo8`. El puerto USB de cada placa se selecciona en Thonny; no es un GPIO.

El 3 de noviembre se validó MQTT/Firebase con sensores y salidas simulados en PC, bajo el prefijo independiente `petcare/equipo8/simulacion/ID_EJECUCION`. Esa prueba no cambia los estados físicos de esta tabla ni calibra la celda.

| Componente | Tipo | Pin ESP32 principal | Publicación / campo | Suscripción / acción | Unidad o rango | Estado |
|---|---|---|---|---|---|---|
| Celda 5 kg + HX711 | Sensor | DT 19, SCK 18 | `/telemetry`: `status.weight_g`, `raw`, `hx_ok` | — | g; capacidad nominal 5000 g, tara/factor pendientes | Lectura RAW confirmada por el equipo; gramos pendientes |
| DHT22 | Sensor | DATA 4 | `/telemetry`: `temperature_c`, `humidity_pct`, `dht_ok` | — | °C y %HR; rango real por verificar | Pendiente físico |
| PIR | Sensor | OUT 27 | `/telemetry`: `pir` | — | booleano | Confirmar modelo/VCC |
| Flotador | Sensor | 26 a GND, pull-up | `/telemetry`: `water_available` | — | booleano; LOW=agua en configuración | Sensor de nivel pendiente; verificar sentido al instalar |
| MG995 | Actuador | PWM 33 | `/ack` y `status.state` | `/commands`: `feed` | consignas 30/75; no son ángulos medidos; ajustar recorrido | Pendiente con compuerta |
| Bomba 3–5 V + módulo MOSFET | Actuador | SIG 23 | `/ack` y `status.state` | `/commands`: `water`, `stop_water` | pulso 1200 ms; límite 2000 ms | LED del módulo probado; bomba pendiente de diodo y cable |
| LED RGB cátodo común | Actuador | R16, G17, B21 | Estado derivado de sensores | `/commands`: `signal_dog`; resto local | blanco 1.5 s por IA; después estado local | Pendiente físico |
| Buzzer activo | Actuador | 22 | Aviso de fin de alimento | Sin tópico propio; lógica local | ON/OFF, aviso 100 ms | Confirmar driver/consumo |
| ESP32-CAM OV2640 + MB | Cámara independiente | Bus interno; no TX/RX a DevKit | HTTP `/stream` → PC; puente consulta `/api/status` y publica `/vision` | GET `/foto` o `/stream` | JPEG VGA 640×480, calidad 12 | Streaming probado; detección móvil de perro/persona confirmada por el equipo |

Los sufijos de tópico se concatenan al prefijo anterior. Los campos de sensores están dentro de `status` en el mensaje de telemetría.
Las órdenes usan JSON con `id` único y `action`; ejemplo: `{"id":"prueba-001","action":"feed"}`.
El firmware bloquea alimento sin calibración y bloquea bomba sin agua. No hay dispensado periódico autónomo implementado.
Cámara: HTTP comprobado anteriormente. Ya existe modo JPEG por MQTT y prueba de transporte en PC; falta cargarlo y verificarlo en la cámara física.

## Alimentación y montaje

- DevKit por USB durante pruebas. HX711 y DHT22 a 3V3/GND; señales del ESP32 a 3.3 V.
- MG995 rojo a +5 V externo, marrón/negro a V−, naranja/amarillo a GPIO33. V− unido a GND de DevKit; no unir V+ al VIN si DevKit está por USB.
- La base ESP32CAM-MB programa la cámara por USB. No se requiere FTDI.
- Confirmar VCC del PIR por modelo; no conectar una salida de 5 V directamente al ESP32.
- Bomba mediante MOSFET lógico y diodo de rueda libre; nunca directo al GPIO.
- Jarra azul: comida. Bote rojo: agua. Montaje propuesto con bomba, sin salida inferior abierta; confirmar que la bomba sea sumergible. El embudo abierto no detiene el flujo.
- Caja de coroplast con soportes rígidos para depósitos y celda; electrónica separada del agua.

## Dato → acción implementada

| Dato/evento | Acción |
|---|---|
| Báscula no calibrada o peso no disponible | Rechazar `feed` |
| Peso ≥250 g | Rechazar nuevo dispensado (umbral inicial, ajustar) |
| `feed` autorizado | Abrir compuerta 900 ms, cerrar, esperar 350 ms y retirar PWM |
| Falta de agua | Apagar/bloquear bomba y LED rojo |
| Bomba llega al tiempo límite | Apagar bomba |
| Presencia PIR, con agua y báscula calibrada | LED azul; no dispensar automáticamente |
| Fin de alimento | Aviso de buzzer 100 ms |
| Ctrl+C en firmware principal | Cerrar recursos y apagar salidas según `safe_shutdown()` |

## Corte del 8 de noviembre

Servo sin carga y LED del MOSFET reportados como funcionales por el equipo. No equivalen a compuerta cargada ni bombeo. [Montaje, resistencias y conexiones](MONTAJE_Y_CONEXIONES.md).

La orden `signal_dog` solo activa RGB blanco por 1.5 s y emite ACK. Está probada con la FSM simulada. El ACK no mide la luz ni confirma físicamente el circuito.
