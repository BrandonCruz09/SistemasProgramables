# Cloud Firestore en PetCare

Actualización del 8 de noviembre de 2026. La docente pidió Cloud Firestore; este es ahora el servicio de la entrega. La prueba anterior con Realtime Database se conserva como antecedente y no se presenta como prueba de Firestore.

## Configuración realizada

- Proyecto existente `petcare-equipo-08`, plan Spark sin facturación.
- Firestore Standard, base `(default)`, ubicación `nam5`.
- Acceso denegado por defecto. Solo el UID de Firebase Auth de la PC puede leer y escribir bajo `petcare/equipo8`. No se publicaron tokens ni reglas abiertas.
- Las reglas de ejemplo están en `firebase/firestore.rules`. `OWNER_UID` es un marcador: la copia local desplegada contiene la identidad existente, excluida de Git.
- `servidor/firestore_rest.py` utiliza ID token y la API REST. Renueva la sesión mediante el cliente Auth existente. No utiliza claves administrativas que evadan las reglas.
- `server_config.example.json` muestra el proveedor Firestore. El perfil privado `server_mqtt_config.json` tiene Firestore activado. `INICIAR_PC.cmd` sigue siendo el lanzador del escritorio.
- No se cargó firmware ni se cambiaron las conexiones físicas durante esta actualización.

## Datos que se guardan

| Ruta bajo petcare/equipo8 | Contenido |
|---|---|
| estado/latest | Última telemetría guardada |
| estado/estado_actual | Telemetría y estado de visión |
| estado/vision | Resumen de detección, sin JPEG |
| estado/command | Orden remota, solo si existe |
| lecturas/{id} | Histórico con received_at |
| eventos_ia/{id} | Detección, confianza, orden y ACK |
| events/{id} | Registro de telemetría |
| simulacion/{ejecucion}/... | Pruebas separadas, marcadas simulated |
| resumen/prueba_firestore | Resultado de validación, no medición física |

El video permanece en Wi-Fi local y la IA en la PC. No se envían imágenes ni video a Firestore. El dashboard mantiene los datos locales recientes; el estado periódico en la nube se actualiza como máximo una vez por minuto por canal. Las decisiones IA y sus confirmaciones se guardan al ocurrir.

## Cuota y funcionamiento sin gasto

Firestore Standard tiene cuota gratuita: 1 GiB almacenado, 50000 lecturas y 20000 escrituras diarias, además de otros límites. El proyecto continúa en Spark: no se activó Blaze, facturación, Storage ni copias programadas. Verificar siempre la consola antes de modificar el plan.

El cliente reserva un máximo local de 10000 escrituras y 20000 lecturas diarias, guardado en `.firestore_budget.json`. La reserva del histórico cuenta hasta 120 lecturas por consulta. El día corresponde a la zona de reinicio de cuota de Firestore, America/Los_Angeles. El contador sobreestima operaciones fallidas y no incluye otras aplicaciones ni las lecturas de la consola; no es un medidor de facturación. Ejecutar una sola instancia del puente por carpeta. No borrar el contador para eludirlo.

Las consultas de comandos tienen intervalo mínimo de 30 segundos. Si se agota la cuota o falla la red, se informa el error y MQTT local puede continuar. No hay reenvío persistente: las escrituras fallidas no se recuperan automáticamente. No se deben declarar esos registros como guardados. Se conserva el histórico sin borrado automático; revisar Uso y exportar o depurar de forma autorizada cuando crezca.

## Qué se comprobó

49 pruebas unitarias pasaron. El archivo `PRUEBA_FIRESTORE_MQTT_2026-11-08.json` contiene 22 comprobaciones con Firestore real y broker real: escritura, lectura, bloqueo sin token, bloqueo fuera de la ruta del equipo, renovación de sesión, actualización parcial, consulta de histórico, JPEG por MQTT, OpenCV, decisión IA de ejemplo, señal RGB simulada, ACK y persistencia de telemetría.

El modelo ejecutó inferencia sobre un JPEG sintético; el resultado de perro se inyectó para probar la decisión. No mide exactitud del detector. La cámara y el actuador de esta prueba son simulados, no el hardware del equipo. Los timestamps UTC pueden indicar 9 de noviembre; en León la ejecución fue el 8 de noviembre.

La prueba de arranque con Firestore activado también pasó: video 8765 y panel 8766 responden sin datos físicos disponibles. Falta cargar la versión MQTT en ambas placas y demostrar telemetría y ACK físicos, calibrar gramos, probar compuerta y bomba y terminar carcasa.

## Continuación exacta

1. Seguir los pasos 1 a 3 del Word personal: RGB, permisos de red y carga de archivos a DevKit y ESP32-CAM.
2. Ejecutar `INICIAR_PC.cmd` una sola vez. Debe indicar `Nube: firestore`.
3. Ver video en el celular y observar el RGB físico al detectar perro. Verificar el mismo id en orden y ACK.
4. En Firebase abrir Firestore > Datos > petcare > equipo8. Revisar `estado/estado_actual`, `lecturas` y `eventos_ia`, fuera de `simulacion`.
5. Esperar hasta un minuto para el registro periódico. Comparar timestamp y valores con el panel; guardar capturas. Un ACK confirma el programa, no que físicamente haya prendido el LED.
6. No mostrar gramos inventados: la báscula debe calibrarse antes de presentar medidas en g.

## Repetir pruebas de software

Desde `servidor`, con el entorno y perfil privado existentes:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -p "test_*.py" -q
.\.venv\Scripts\python.exe probar_firestore_mqtt.py
.\.venv\Scripts\python.exe iniciar_integracion.py --check
```

La prueba de nube lee `server_firestore_config.json`, excluido de Git. No copiar credenciales en la página ni el firmware. RTDB anterior no se borró ni se migró como si fueran mediciones nuevas.

Fuentes oficiales: [cuota y precios](https://firebase.google.com/docs/firestore/pricing), [API REST y autenticación](https://firebase.google.com/docs/firestore/use-rest-api), [consulta de documentos](https://firebase.google.com/docs/firestore/reference/rest/v1/projects.databases.documents/list).
