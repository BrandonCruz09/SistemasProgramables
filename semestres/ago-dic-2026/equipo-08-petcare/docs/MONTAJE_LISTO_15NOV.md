# PetCare listo para cargar y comprobar

15 de noviembre de 2026. Se preparó el software para el montaje. No se cargaron estas nuevas versiones a las placas ni se movieron actuadores durante esta preparación.

## Cambios y comprobaciones

- Servo GPIO33: **1850 us cerrado / 800 us abierto**, a 50 Hz. Posiciones observadas por el equipo. El programa principal ya no usa la prueba de 3000 us ni convierte estos valores a grados. La apertura sigue limitada a 900 ms; la porción está sin medir.
- Pesa: se conservan **tara −428929.16** y **factor 285.80386 cuentas/g**. Referencia nominal de galletas de 163 g; calibración aproximada. No se recalibró. [Validación e integración previas](CALIBRACION_FIRESTORE_14NOV.md).
- OLED SSD1306 128×64 reutilizada de Nebula Dash. Usa pines libres y muestra peso neto con una decimal. Distingue SIN LECTURA, SIN CALIBRAR y lectura en pausa durante el bombeo. Si falta la pantalla, el resto del programa continúa.
- Panel HTTP: incorpora el video procesado, además de gramos, sensores, órdenes manuales y estado de Firestore. La IA detecta perro/persona; no reconoce perros individuales ni dosifica automáticamente por detectarlos.
- La PC usa JPEG por MQTT de la cámara y lo presenta como video MJPEG para el celular. No se garantiza una tasa de cuadros: depende del hardware y de la red.
- Se corrigió un fallo de arranque de visión cuando se usa MQTT y no existe URL HTTP de cámara.
- **73 pruebas de software aprobadas**. **7 comprobaciones locales** aprobaron servicios web, JPEG por MQTT, modelo real, MJPEG, peso simulado en panel y pérdida de señal. [Resultado](PRUEBA_PREPARACION_15NOV.json). Esta prueba usó una imagen sintética y no activó GPIO ni escribió Firestore.
- Firestore conserva su configuración privada anterior. No se habilitó facturación. [Prueba real anterior de guardado y consulta](PRUEBA_PESA_FIRESTORE_2026-11-14.json).

## Pantalla y señales

Conectar por el nombre impreso en cada módulo, no por la posición izquierda/derecha de sus patas. Hacer las conexiones sin alimentación.

| Componente | Terminal | ESP32 normal |
|---|---|---|
| OLED SSD1306 | VCC | 3V3 |
| OLED SSD1306 | GND | GND |
| OLED SSD1306 | SDA | GPIO26 / D26 |
| OLED SSD1306 | SCL | GPIO25 / D25 |
| HX711 | VCC / GND | 3V3 / GND |
| HX711 | DT / SCK | GPIO19 / GPIO18 |
| DHT22 módulo | DATA | GPIO4; conservar VCC3V3 y GND según sus etiquetas |
| PIR | OUT | GPIO27; conservar su alimentación ya identificada |
| Servo MG995 | Señal | GPIO33 |
| Relé HW-383 | IN1 | GPIO23, activo LOW; conservar montaje de potencia validado |
| Buzzer | Señal de control | GPIO22; conservar driver/alimentación según el módulo |
| RGB cátodo común | R / G / B | GPIO16 / GPIO17 / GPIO21, cada color con su resistencia |

La OLED tiene bus exclusivo: no usar GPIO21/22 de Nebula Dash, pues aquí controlan RGB y buzzer. No se requiere MPU6050. Se reutiliza el controlador ssd1306.py del juego.

El servo toma +5 V de la fuente externa y su negativo va a V−. V− se une a GND del ESP32. La tierra de protección de la fuente no reemplaza V−. Durante las pruebas, alimentar cada placa por su USB; no alimentar VIN con la fuente externa al mismo tiempo. La bomba no toma potencia de un GPIO ni del riel 3V3.

## Archivos de cada equipo

En el escritorio, **PetCare_Listo_15nov** contiene:

- `01_ESP32`: main.py y módulos del programa, pantalla_peso.py, ssd1306.py, ambos JSON de calibración, perfil local y carpeta umqtt.
- `02_ESP32CAM`: main.py, camara_wifi.py, camara_mqtt.py, configuración Wi-Fi/MQTT y umqtt. Requiere conservar el firmware especial que ya tiene el módulo camera; no instalar MicroPython genérico.
- `1_PREPARAR_RED.cmd`: comprueba que la PC esté en la red elegida y escribe su IP en las copias que se cargarán a las placas. No carga ni ejecuta nada en las placas.
- `2_INICIAR_PETCARE_PC.cmd`: prepara la IP e inicia Mosquitto, visión y puente. Mantener la ventana abierta; Ctrl+C detiene los servicios.
- `CORREGIR_RED_LOCAL.cmd`: si Windows bloquea las conexiones del celular o de las placas, prepara reglas limitadas a la red local para MQTT y los dos puertos web; pide administrador.
- Guía Word y accesos al panel/cámara, creados o actualizados al preparar la red.

La carpeta del escritorio contiene configuraciones privadas; en Git se publica el código y las plantillas, no las contraseñas.

## Orden para mañana

1. Conectar PC y celular a la red doméstica elegida de 2.4 GHz. Las ESP32 clásicas no admiten Wi-Fi de 5 GHz. Una PC/celular en 5 GHz del mismo router puede comunicarse si no hay aislamiento entre bandas, pero para la primera prueba conviene usar la misma red.
2. Ejecutar `1_PREPARAR_RED.cmd`. Si indica una red diferente, conectar la correcta antes de continuar. Anotar la IP de `IP_ACTUAL.txt`.
3. Con fuente de motores apagada, conectar solo el ESP32 normal por USB. Abrir Thonny, seleccionar MicroPython ESP32 y el puerto correspondiente. Copiar **todo el contenido** de `01_ESP32` a la raíz del dispositivo, incluida umqtt y los dos JSON. No copiar la carpeta contenedora ni solo main.py. La copia puede sustituir archivos de PetCare anteriores; no borrar la memoria completa.
4. Abrir main.py del ESP32 y ejecutarlo con F5. Debe iniciar con bomba apagada y servo sin PWM. Revisar OLED y gramos. Si está vacío y no vuelve cerca de cero, comprobar apoyo/roces antes de retarar. No volver a calibrar con 163 g sin tener la referencia colocada.
5. Detener con Ctrl+C. Conectar la cámara mediante ESP32CAM-MB y USB de datos, seleccionar su puerto y copiar el contenido de `02_ESP32CAM` a su raíz. No borrar ni cambiar el firmware de cámara. Reiniciar esa placa cuando se quiera iniciar video.
6. Ejecutar `2_INICIAR_PETCARE_PC.cmd` y luego mantener ambos main.py en ejecución. Las ESP32 se comunican por Wi-Fi; no se conectan por TX/RX entre ellas. El servidor PC debe permanecer encendido para IA, página unificada y Firestore.
7. Abrir `ABRIR_PANEL.url` en la PC o escribir `http://IP_DE_LA_PC:8766/` en el celular. Incluye cámara y gramos. La vista de cámara independiente está en el puerto 8765. No poner localhost en el teléfono.
8. Si PC abre pero celular no, ejecutar `CORREGIR_RED_LOCAL.cmd` y aceptar el aviso de administrador de Windows. Verificar también que no sea una red de invitados ni tenga aislamiento de clientes.
9. Con el mecanismo libre, energizar servo y probar una sola orden de alimento sin croquetas; debe apartarse a 800 us y volver a 1850 us. Después probar con pocas croquetas y vigilar atascos. Los valores de posición están observados, pero todavía no se validó la dosis ni el cierre bajo carga.
10. Revisar DHT22: en la captura anterior no respondió. Comprobar después PIR, RGB y buzzer con el montaje real. Medir el volumen de agua: los 15 s son una referencia sin calibrar y no garantizan 500 ml. No se usa flotador.

Si cambia la IP de la PC, ejecutar de nuevo el preparador y volver a cargar `config_local.py` en el ESP32 y `mqtt_config.py` en la cámara. Los archivos de calibración no cambian al preparar la red.

Fuente de compatibilidad Wi-Fi: [datasheet oficial ESP32](https://documentation.espressif.com/esp32_datasheet_en.html).
