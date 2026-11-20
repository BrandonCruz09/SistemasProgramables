# Firmware activo del 19 de noviembre

Esta carpeta contiene la revisión r3 del firmware. La revisión anterior se cargó al ESP32; r3 todavía no se ha cargado ni probado físicamente. `../esp32` conserva el código anterior y sus pruebas históricas. No mezclar los módulos de ambas versiones.

## Uso

Copiar los archivos Python y `calibracion_validada.json` de esta carpeta a la raíz del ESP32; crear `config_local.py` a partir del ejemplo sin publicarlo. `main.py` ejecuta el proyecto; en Thonny se pueden ejecutar por separado `prueba_servo.py`, `prueba_bomba.py`, `prueba_manual.py` o `prueba_pesa.py`. Detener una prueba antes de iniciar otra. El panel de PC requiere el servidor actualizado de este repositorio.

- Servo GPIO33, 50 Hz: abrir 1350 us, cerrar 1690 us. Conserva PWM hasta salir.
- Relé IN1 GPIO23, activo LOW, máximo 5 s. Temporizador y comprobación en bucle apagan la salida.
- Buzzer GPIO22: pasivo confirmado físicamente; aviso nuevo de dos notas a 1000 y 1500 Hz.
- DHT GPIO4, PIR GPIO27, HX711 DT19/SCK18, OLED SDA26/SCL25. Sin RGB ni flotador.
- `gate_test_open`: prueba sin croquetas, sin corte por peso; cierre manual. No usar para servir alimento. `gate_open` y `feed` conservan el corte a 300 g.
- MQTT rechaza órdenes retenidas, duplicadas o de sesiones anteriores; la PC reemplaza la espera por el ACK real.

## Peso y alcance de la comprobación

Se preservó la referencia del 14 de noviembre: factor 285.80386 y tara -428929.16. El archivo es idéntico al respaldo histórico. No hay tara automática ni sobrescritura por archivos antiguos.

El tazón vacío sigue indicando aproximadamente 1470–1507 g. La referencia histórica NO está validada para el montaje actual. `prueba_pesa.py` permite leer RAW y crear una propuesta después de comprobar cero, carga conocida y repetición, sin reemplazar la referencia activa. El dato nominal anterior de 163 g era aproximado.

Revisión r3: 40 pruebas del firmware y 8 del panel y ACK pasaron en PC. Se probaron errores de inicio, red, pantalla, cierre y apagado. Se ordenó el formato del firmware, se aislaron fallos de servicios y se añadió el estado ERROR_SALIDAS para no informar LISTO cuando falla el cierre. Las siguientes comprobaciones en placa pertenecen a la revisión anterior. En el ESP32 real se verificaron PWM de 50 Hz y pulsos acordados, corte de salida del relé a 5004 ms, DHT y MQTT. El usuario confirmó sonido con PWM; luego se cambió a dos notas, pendiente de escucha de esa nueva secuencia. Servo y bombeo siguen pendientes de funcionamiento físico; un ACK no demuestra movimiento ni flujo. No hay medición de volumen.

Ejecutar pruebas de PC: `python -m unittest discover -s tests`. Las pruebas usan dobles de hardware y no mueven dispositivos.
