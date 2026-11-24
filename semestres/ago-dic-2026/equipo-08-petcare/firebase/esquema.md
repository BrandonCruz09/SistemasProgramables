# Esquema de Cloud Firestore de PetCare

## Servicio y autenticación

El servicio elegido para la entrega es **Cloud Firestore**, no Realtime Database. El servidor Python de la PC utiliza la API REST de Firestore y un token de Firebase Authentication. El navegador del teléfono consulta el panel local; no recibe credenciales de Firebase. Las reglas requieren autenticación y limitan lectura/escritura al UID de la PC configurado en la copia privada. El marcador `OWNER_UID` del archivo de reglas versionado no es un UID válido y no debe desplegarse sin reemplazarlo.

La configuración descrita en `docs/FIRESTORE_2026-11-08.md` se hizo con el plan Spark. No se deben publicar tokens ni perfiles privados. El registro local de cuota limita las solicitudes del proceso PetCare, pero no mide todo el uso del proyecto Firebase.

## Colecciones y documentos

Las rutas se encuentran bajo `petcare/equipo8`:

| Ruta | Uso |
|---|---|
| `estado/latest` | Última telemetría guardada |
| `estado/estado_actual` | Estado operativo y marca de actualización |
| `estado/vision` | Resumen de detección; no contiene video |
| `estado/command` | Última orden, cuando se persiste |
| `lecturas/{id}` | Telemetría histórica con hora de recepción, unidad y campos de sensores |
| `eventos_ia/{id}` | Detección, confianza, acción asociada y ACK, cuando existe |
| `eventos_agua/{id}` | Inicio, fin y motivo de término del pulso de agua |
| `events/{id}` | Eventos operativos de la integración |
| `simulacion/{run}/...` | Datos de pruebas de software, separados y marcados como simulados |

Un registro incluye campos como `received_at`, `weight_g`, `weight_unit`, `raw`, `hx_ok`, `calibrated`, temperatura/humedad, `pir`, estado del relevador y la marca `simulated` cuando corresponde. Un valor `null` señala que no hubo lectura; no se convierte en cero. Los cuadros de cámara y el video se quedan en la red local.

## Evidencia disponible y alcance

- `docs/PRUEBA_FIRESTORE_MQTT_2026-11-08.json` registra 22 comprobaciones sobre Firestore y broker reales. La telemetría, JPEG, detección y respuesta de placa de esa cadena se simularon; el archivo lo marca `simulated: true`.
- `docs/PRUEBA_PESA_FIRESTORE_2026-11-14.json` registra 22 verificaciones con una lectura de HX711 real transmitida por USB a la PC, MQTT y luego Firestore. La misma telemetría se leyó de vuelta y se comprobó que la lectura sin credenciales fuera rechazada. La prueba no activó salidas ni comprueba el Wi‑Fi de la placa.
- No se presenta esa captura como calibración exacta: el paquete reportado como 163 g no se verificó con otra báscula. Tampoco representa una prueba completa del equipo ensamblado.

La escritura/lectura en Firestore está implementada y tiene evidencia previa. Antes de la presentación actual, verificar en consola y en el panel que la PC tenga Internet, que el perfil privado siga activo y que una lectura nueva aparezca con hora reciente. Si falla la red, el puente puede seguir recibiendo MQTT local, pero no se debe describir el evento que falló como guardado en la nube.

## Protección de datos y costos

No activar Blaze, Storage, exportaciones programadas ni facturación para ejecutar esta entrega. Mantener autenticación y reglas restrictivas; no abrir lectura/escritura pública. No añadir contraseñas, tokens o UID privado a Git. Firestore guarda datos y estados, no imágenes. Revisar periódicamente el uso y la cuota en Firebase.
