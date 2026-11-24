# Montaje y conexiones actuales de PetCare

## Orientación física

Vista frontal: mirando el dispensador desde el lado de los platos, el recipiente de alimento queda a la izquierda y el de agua a la derecha. La electrónica va en un compartimiento seco, separada de los recipientes y de cualquier salida de agua. La cámara queda arriba y al frente, con lente libre para ver el área de los platos. El depósito de croquetas queda sobre el plato izquierdo; la compuerta accionada por el MG995 solo debe abrir dentro de la base de madera.

La ubicación es una propuesta de distribución basada en las fotos del cascarón. No es una plantilla a escala: antes de atornillar placas, revisar dimensiones, movimiento de tapa y que el peso del tazón no toque la carcasa.

## Energía y tierra común

Cambiar conexiones con la fuente desenchufada. La fuente mostrada tiene entrada de red y salida de corriente directa. No dejar sus terminales de red expuestos ni colocarla en la zona húmeda. Si no cuenta con cubierta, fijación y cableado seguro, mantenerla fuera del equipo y pedir a una persona calificada que revise la entrada de red.

- **V+ de salida (5 V):** positivo de baja tensión para las cargas que admitan 5 V, como el MG995 y la bomba mediante el relevador.
- **V− de salida:** negativo común. Se lleva al riel negativo de la protoboard y a GND de la ESP32 DevKit; desde esa referencia vuelven las señales del módulo de relevador y las cargas de baja tensión.
- **Símbolo `⏚`:** tierra de protección de la fuente. No es el negativo de 5 V ni la tierra de señal; no lo conectes al riel de GND del protoboard.
- **ESP32 por USB:** durante programación y pruebas, no unir también V+ externo a VIN/5V de la placa. Sí unir GND de la DevKit con V− para compartir referencia de señal.
- Los rieles de la protoboard pueden estar partidos a la mitad; verificar continuidad. No alimentar el servo o la bomba a través de pistas finas del protoboard. Llevar su positivo y retorno en cables directos a sus terminales o a una conexión de potencia firme; el protoboard solo sirve como punto de distribución de baja corriente/señal.

## DevKit, sensores y compuerta

| Señal/componente | Conexión exacta en la DevKit | Alimentación |
|---|---|---|
| DHT22 | DATA al GPIO4 | VCC a 3V3; GND a GND común |
| PIR | OUT al GPIO27 | VCC según la serigrafía del módulo; GND común. Confirmar que OUT no exceda 3.3 V |
| HX711 | DT/DOUT al GPIO19; SCK al GPIO18 | VCC a 3V3; GND a GND común |
| MG995 | Cable de señal naranja/amarillo al GPIO33 | Rojo a +5 V de la fuente; café/negro a V−. Unir ese V− a GND de DevKit |
| Relevador HW-383 K1 | IN1 al GPIO23; GND lógico al GND común | Con el puente entre VCC y RY-VCC retirado como en el módulo fotografiado: RY-VCC a +5 V, VCC a 3V3 y GND a GND común. No conectar 5 V a una entrada lógica sin verificar la placa |
| Buzzer pasivo | S/señal al GPIO22 | VCC y GND a los terminales del módulo según su serigrafía; común GND |
| OLED SSD1306 (solo si está instalada) | SDA al GPIO26; SCL al GPIO25 | VCC/GND de acuerdo con el módulo |

No conectar 5 V a ningún GPIO ni a 3V3. El GPIO del servo es solo señal; la corriente del motor debe venir de su fuente externa. Los valores guardados del servo son 850 µs abierto y 1500 µs cerrado a 50 Hz. El deslizador del panel envía posiciones dentro de ese intervalo. Si vibra, golpea el límite mecánico o hace esfuerzo, detenerlo y apagar la fuente; no extender los límites por software.

## Celda de carga

El tazón descansa únicamente en la plataforma unida al extremo móvil de la celda. La celda se fija por un extremo a la base rígida y por el otro a la plataforma; debe quedar espacio para flexionar sin tocar madera, carcasa ni tornillos. Mantén los cables sin tensión y lejos de la bomba y el servo.

| HX711 | Placa |
|---|---|
| VCC | 3V3 |
| GND | GND común |
| DT/DOUT | GPIO19 |
| SCK | GPIO18 |

El código conserva el archivo `firmware/esp32_v2/calibracion_validada.json` y no cambia la tara automáticamente. La referencia nominal de 163 g no quedó verificada con una báscula independiente; antes de afirmar precisión, hacer una comprobación con una masa conocida. No borrar ni recalibrar el archivo solo para quitar una lectura extraña; primero revisar montaje, contactos y antigüedad de telemetría.

## Relevador, bomba y diodo

El relevador se controla con GPIO23 y la bomba se alimenta desde la fuente externa, nunca desde un GPIO. Para el contacto K1 usar los bornes identificados en la placa o confirmar COM/NO con el diagrama del módulo. La línea de +5 V de la bomba pasa por COM y NO de K1; el otro cable de la bomba va al V− de la fuente. No usar NC para esta función. La lógica del firmware limita una orden a 5 s, pero la prueba física de corte debe hacerse con agua y bajo supervisión.

Colocar el diodo 1N4007 en paralelo con la bomba: la pata con franja al positivo de la bomba (lado que recibe +5 V cuando K1 cierra) y la pata sin franja al negativo de la bomba/V−. Aislar las patas para que no se toquen. La bomba debe ser sumergible y trabajar dentro del agua. Guiar la manguera hacia el tazón derecho, fijada y sin dirigirla a la electrónica. No operar en seco ni dejar la bomba sin vigilancia.

## Cámara y acceso desde el teléfono

La ESP32-CAM y la DevKit son placas distintas. La cámara se alimenta por la base MB/USB durante programación o por una fuente regulada de 5 V a sus pines 5V y GND cuando trabaje sin USB, pero no por ambas vías al mismo tiempo. No necesita cables TX/RX entre placas: la cámara entrega video por Wi‑Fi y el servidor de la PC procesa los cuadros. La PC, la cámara y la DevKit deben estar en la misma red local de 2.4 GHz; el teléfono usa la dirección local de la PC y el puerto del panel. La red guardada INFINITUM3EAE no estaba disponible en la última comprobación del equipo, así que aún no se puede decir que la integración esté probada allí.

## Comprobación antes de energizar

1. Apaga y desenchufa la fuente externa.
2. Comprueba que V−, GND de DevKit, GND lógico del relevador y retornos de cargas estén identificados por serigrafía; no uses el símbolo `⏚` como V−.
3. Revisa que no exista continuidad accidental entre V+ y V− y que la franja del diodo esté en el lado positivo de la bomba.
4. Conecta solo USB y revisa telemetría; después prueba por separado el buzzer, el servo sin carga y el relevador con la bomba apartada.
5. Prueba bomba solo con agua y recipiente con espacio, y observa que se apague realmente al concluir los 5 s.
6. Prueba alimento con el tazón y soporte libres, una masa conocida y la tapa montada. No armes automatización hasta verificar cierre y lectura.
