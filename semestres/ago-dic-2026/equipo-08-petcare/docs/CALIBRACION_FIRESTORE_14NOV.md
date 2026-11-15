# Calibración integrada y prueba de Firestore

14 de noviembre de 2026, hora de México. Los registros técnicos usan UTC; por eso muestran 15 de noviembre.

## Cambios realizados

El firmware principal recupera el factor y la tara desde dos archivos persistentes. La tara más reciente de `tara_tazon.json` tiene prioridad. Si los datos faltan o son inválidos, el sistema deja el peso sin calibrar y conserva el bloqueo de alimento. No se sobrescribió la configuración privada de red.

- Tara actual: **−428929.16 cuentas**.
- Factor: **285.80386 cuentas/g**.
- Referencia declarada: paquete de galletas de **163 g**. Su masa bruta no se contrastó con otra báscula; la calibración queda marcada como aproximada.
- Validación anterior: tazón vacío entre −0.081 y +0.149 g; mismo paquete entre 163.024 y 163.296 g. No se repitió ni cambió la calibración en este corte.

Se protegieron los pulsos del reloj HX711 contra interrupciones y se rechazan lecturas saturadas. La telemetría incluye `weight_g`, `weight_unit`, `calibrated`, `calibration_approximate` y `calibration_reference_g`. La rutina manual de calibración ahora guarda los JSON utilizados por el programa; ya no pide copiar números a config.py.

## Verificación realizada

Se cargaron los archivos del firmware al ESP32 por COM3 y se compararon con la copia local. Se ejecutó solo SensorHub, sin inicializar servo ni bomba. Hubo 12 lecturas válidas de peso, entre 22.462 y 23.054 g. La última fue **22.462784 g**. No se conoce qué carga tenía el tazón durante esta captura; no es una nueva validación del cero.

El DHT no respondió: `dht_ok=false`, temperatura y humedad nulas. El PIR devolvió `false`; no hubo prueba física de detección de movimiento. No se usa flotador: nivel de agua nulo y `water_level_monitored=false`.

Recorrido comprobado: **ESP32 físico → USB → PC → MQTT local → puente → Firestore real → consulta autenticada**. También se consultó la API HTTP del panel. El dato de peso se conservó exactamente. Pasaron **22 comprobaciones de integración** y **66 pruebas automatizadas** de software. El cliente MQTT de esta prueba fue la PC; falta validar la publicación inalámbrica directa de la placa en el montaje completo.

Firestore conservó peso, unidad, lectura RAW, banderas de sensores, referencia de calibración, fecha, estado actual e historial. Las solicitudes de lectura y escritura sin autenticación fueron rechazadas. La prueba usó la configuración existente; no habilitó facturación ni servicios nuevos.

Ruta lógica de prueba: `petcare/equipo8/pruebas/pesa-8e435d6844`.

Documento consultado: `petcare/equipo8/pruebas/pesa-8e435d6844/estado/latest`.

## Evidencia y reproducción

- [Captura física](CAPTURA_PESA_INTEGRADA_2026-11-14.json).
- [Comprobaciones contra Firestore](PRUEBA_PESA_FIRESTORE_2026-11-14.json).
- [Cero previamente validado](verificacion_cero_reajustado.json).
- [Repetición del paquete de referencia](verificacion_paquete_despues_tara.json).
- [Guía personal en Word](PetCare_Calibracion_y_pendientes_14nov.docx).

Con motores sin alimentación, `mpremote connect COM3 run firmware/pruebas/capturar_pesa_integrada.py` imprime la captura. Guardar el objeto JSON que sigue a `PESA_CAPTURA` en un archivo. Desde servidor, ejecutar `python probar_pesa_firestore.py RUTA_CAPTURA RUTA_REPORTE` con el entorno del proyecto y el perfil privado configurado. Cada ejecución crea otra ruta de prueba y consume operaciones de Firestore; no ejecutarlo continuamente.

## Lo que sigue en el montaje

1. Mantener apagada la fuente del servo mientras se fija. La señal actual es GPIO33; rojo a +5 V externo, marrón/negro a V−, y V− a GND del ESP32. No usar tierra de protección como sustituto de V−. Con USB en la placa, no unir también V+ al VIN.
2. Fijar el cuerpo del servo a un soporte rígido. Ajustar la tapa para que se deslice libremente y no cargue su peso sobre el eje. No forzar el eje con la mano.
3. Antes de acoplar el brazo, hacer una prueba supervisada de posición. Ajustar cerrado y abierto con la compuerta real, sin usar los extremos de pulso como garantía de recorrido. El firmware conserva consignas 30/75 dentro de 1000–2000 us; no son grados medidos.
4. Con el mecanismo libre, probar un ciclo sin croquetas y luego con poca cantidad. Comprobar cierre y ausencia de atoramientos. La orden feed abre 900 ms; todavía falta validar esa cantidad físicamente. Apagar si el servo queda forzado o zumba continuamente.
5. Revisar DHT22: alimentación y GND del módulo, DATA en GPIO4. Respetar las etiquetas del módulo de tres pines. Volver a probar hasta tener dht_ok=true.
6. Una vez inmóvil la base, revisar tazón vacío y la referencia. Si aparece un desfase, primero comprobar roces, apoyo del plato y cables tensos; no cambiar el factor para ocultarlo. La lectura actual de 22.46 g debe contrastarse con la carga real.
7. Repetir el recorrido completo por Wi-Fi con ambas placas y la PC. Revisar peso en panel y Firestore, cámara e IA, orden de alimento y confirmación. La detección de perro no debe tomarse como confirmación de que cayó alimento.
8. Medir el agua realmente servida antes de afirmar 500 ml. Los 15 s actuales son una referencia nominal, sin flotador ni caudal calibrado. El display queda pendiente para después de terminar el montaje.
