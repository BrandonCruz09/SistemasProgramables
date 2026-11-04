# Firebase y prueba de ESP32 simulada

Avance del 3 de noviembre de 2026, horario de Mexico. Equipo 08.

Se creo el proyecto `petcare-equipo-08` en Firebase Spark y una instancia de **Realtime Database**, en Estados Unidos (us-central1). Se comprobo escritura y lectura reales en la nube. Las lecturas, presencia y actuadores de esta prueba son simulados en la PC; no se conectaron placas ni se calibro la bascula.

## Costo y eleccion de base

La consola muestra Spark, sin costo (USD 0 al mes). No se vinculo facturacion, no se activo Blaze y no se habilitaron Firestore, Hosting, Storage ni Cloud Functions. Spark tiene cuotas; no es almacenamiento ilimitado. Esta prueba termina por si sola y guarda objetos pequenos, sin fotos ni video.

El material `Sist Progr Unidad4 Firebase.pdf` identifica Realtime Database en su portada y en la pagina 2; la pagina 3 menciona Spark gratuito. Firestore es otra base dentro de Firebase. No se cambio el proyecto a Firestore por una mencion informal; si la profesora lo exige expresamente, habra que adaptar el cliente y las reglas.

## Recorrido probado

```text
Sensores ficticios -> FSM de PetCare en PC -> MQTT local
                    -> puente Python -> Realtime Database

Orden en Realtime Database -> puente -> MQTT
                           -> FSM con salidas simuladas
                           -> confirmacion MQTT -> Realtime Database
```

Se reutiliza `PetCareController` del firmware, con sensores, servo, bomba, buzzer y LED sustituidos por objetos de software. No es una emulacion electrica de GPIO, PWM, I2C o del ESP32. Se comprueba la logica y el transporte; no la fuerza del servo ni la precision del HX711.

Mosquitto 2.1.2 abre un puerto disponible ligado a `127.0.0.1`, solo en la PC. La prueba inicia ese proceso y lo cierra al terminar; no modifica el servicio instalado ni abre el firewall. Los topicos y la ruta de Firebase incluyen `/simulacion/` y un identificador distinto por ejecucion. No se publican comandos en los topicos del hardware.

## Datos guardados

Raiz de cada ejecucion: `petcare/equipo8/simulacion/ID_EJECUCION`.

| Nodo | Contenido |
|---|---|
| `probe` | Objeto escrito y leido de vuelta para comprobar igualdad. |
| `latest` | Ultima telemetria, con `simulated: true` y dispositivo `esp32-simulado-pc`. |
| `events` | Historial de estados recibido a traves de MQTT. |
| `command` | Ultima orden y respuesta aceptada/rechazada. |
| `vision` | Ejemplo ficticio marcado como simulado; no procede de la camara. |
| `report` | Lista de comprobaciones, resultado global y fechas UTC. |

Los 75 g, 24.5 grados y 55 %HR son valores elegidos para la prueba. `calibrated: true` representa un escenario ficticio; no significa que la celda fisica este calibrada. Los identificadores con 20261104 corresponden a UTC: la ejecucion se hizo el 3 de noviembre por la noche en Mexico.

## Seguridad de esta configuracion

Authentication usa una identidad anonima de Firebase para esta PC. El token de renovacion queda en `.firebase_refresh_token`, excluido de Git. Las reglas permiten leer y escribir solo a su UID y solamente dentro de `petcare/equipo8/simulacion`. El resto permanece bloqueado. Habilitar el proveedor anonimo no concede acceso a otras identidades.

Se verificaron HTTP 401 sin token, rechazo fuera de la carpeta autorizada y renovacion de la sesion manteniendo el mismo UID. No se usan reglas publicas `read: true / write: true`, claves de administrador ni cuentas de servicio. `database.rules.example.json` contiene un marcador; la regla instalada con el UID esta en `database.rules.local.json`, privado.

## Como repetir en esta computadora

1. Tener Internet. No conectar ESP32 ni abrir Thonny para esta prueba.
2. Abrir `PetCare_Firebase` en el escritorio y ejecutar `Probar_Firebase_MQTT.cmd`.
3. Esperar a que aparezca `COMPLETADO`. El programa cierra su broker al finalizar.
4. Abrir `Ver_Firebase.url`. Dentro de `petcare/equipo8/simulacion`, abrir la ejecucion mas reciente y revisar `latest` y `report`.
5. El resultado local queda en `servidor/simulacion_resultado.json`. Si aparece un fallo, no presentarlo como prueba correcta.

En otra PC: instalar Mosquitto desde su web oficial, crear el entorno Python de servidor, instalar requirements.txt y copiar `firebase_sim_config.example.json` a `firebase_sim_config.json`. Completar URL/API key de su proyecto, habilitar Authentication anonimo y autorizar exclusivamente su UID en las reglas. No compartir el token de esta computadora. No sustituir la configuracion de video por la de simulacion.

## Cambios y resultados

El puente acepta prefijo MQTT y raiz de Firebase configurables. Se corrigio la comparacion del codigo de conexion de Paho MQTT v2 y se evitaron URLs con token en los errores de lectura/escritura. Se agregaron simulador, prueba integrada y acceso de inicio.

La ejecucion completa paso 17 comprobaciones contra Firebase real y MQTT local: escritura/lectura, permisos, renovacion, telemetria, historial, alimento, cierre, duplicado, bloqueo por peso, falta de calibracion, falta de agua, orden de agua, apagado por tiempo, detener, accion invalida y ejemplo de vision. El reporte tambien se leyo de vuelta desde Firebase. La suite local paso 19 pruebas de software.

La evidencia reproducible esta en `PRUEBAS_FIREBASE_SIMULADA.json`. No demuestra la integracion fisica ni el flujo real de la camara hacia Firebase. Aun faltan: calibrar sensores, ajustar compuerta, definir cierre del agua, autorizar y probar el entorno real, completar automatizacion y medir estabilidad prolongada.

## Fuentes

- [Planes y cuotas de Firebase](https://firebase.google.com/pricing)
- [Realtime Database y Firestore](https://firebase.google.com/docs/database/rtdb-vs-firestore)
- [Autenticacion REST](https://firebase.google.com/docs/database/rest/auth)
- [Reglas con identidad de usuario](https://firebase.google.com/docs/database/security/rules-conditions)
- [Mosquitto oficial](https://mosquitto.org/download/)
