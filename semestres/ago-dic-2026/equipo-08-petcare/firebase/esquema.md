> Actualización: este esquema RTDB es un antecedente. El servicio final es Cloud Firestore; consultar [configuración vigente](../docs/FIRESTORE_2026-11-08.md).

# Esquema actual de Firebase Realtime Database

Servicio verificado: RTDB, no Firestore. `reglas.json` es una plantilla restringida a simulación, con UID de ejemplo; no se despliega automáticamente y no habilita datos físicos.

Bajo `petcare/equipo8/simulacion/ID_EJECUCION` las pruebas usan `simulated: true`. El hardware previsto usará un ámbito independiente que requiere reglas autenticadas explícitas.

- `lecturas/TIMESTAMP_NS`: telemetría histórica con `received_at` ISO UTC, `device`, `simulated` cuando corresponde y `status`.
- `eventos_ia/ID_COMANDO`: `timestamp`, `deteccion`, `accion`, `confianza`, `estado`, `command`; después `ack` y `acknowledged_at`. Se usa el id de comando como clave para relacionar la confirmación; la fecha queda en el documento/objeto.
- `estado_actual`: `telemetria`, `vision`, `updated_at`.
- `latest`, `vision`, `events`, `command`: rutas anteriores conservadas por compatibilidad.

El cliente del servidor usa Firebase Auth y tokens locales. No incluir tokens, contraseñas ni UID privado en la plantilla pública. El dashboard no entrega esas credenciales al celular. Datos de video no se suben a Firebase; solo lecturas, resultados y eventos.

Las rutas nuevas se guardaron y se leyeron de vuelta en RTDB real con dispositivos simulados el 8 de noviembre de 2026, hora de León. Falta autorizar y probar la ruta física. No se cambió el plan ni se activó facturación. Si la docente exige Cloud Firestore, esta implementación no debe presentarse como Firestore; requiere adaptación específica.
