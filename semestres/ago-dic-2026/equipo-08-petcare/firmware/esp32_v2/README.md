# PetCare · firmware r8

## Seguridad de arranque

- La bomba queda inactiva en nivel HIGH porque el relé K1 trabaja activo en LOW.
- El servo no recibe pulsos al iniciar; el programa no intenta cerrar ni abrir la compuerta durante el arranque.
- La automatización por cámara inicia desarmada después de cada reinicio. Una detección solo informa mientras esté desarmada.
- Para permitir servido automático, habilítalo desde el panel web. La comida se completa hasta 300 g; el agua usa un pulso de 5 s. La opción manual sigue disponible.
- Deshabilitar la automatización cancela solicitudes automáticas pendientes y detiene un servido que se originó en IA.

El firmware manda el nivel seguro al inicializar GPIO, pero no puede fijar el estado eléctrico antes de que MicroPython ejecute `boot.py`. Si el relé se activa al energizar su fuente antes de que arranque la placa, mantén desconectada la bomba y revisa el nivel inactivo de la entrada del módulo; no lo atribuyas solo al código.

## Pines y mecanismo

Servo MG995: GPIO33, 50 Hz, extremos configurados en 850 µs (abierta) y 1500 µs (cerrada). El panel incluye un deslizador para enviar posiciones intermedias dentro de esos extremos. La posición intermedia conserva los límites del servido manual: cierre a 300 g, lectura inválida o tiempo máximo. Ajusta el recorrido con la compuerta libre y detén la prueba si el servo zumba, hace fuerza o llega al tope mecánico.

Relé de bomba: IN1 GPIO23, activo LOW, máximo 5 s por orden. Buzzer GPIO22, DHT22 GPIO4, PIR GPIO27, HX711 DT/SCK GPIO19/18, OLED SDA/SCL GPIO26/25. Sin LED RGB ni flotador.

## Pesa

Se conserva `calibracion_validada.json` (factor 285.80386 cuentas/g, tara −8994.451). El programa no vuelve a calibrar ni tara automáticamente. Esa calibración provino del paquete de 163 g registrado antes; la lectura bajo carga real debe validarse con una masa conocida.

## Carga y prueba

1. Deja desconectada la fuente externa del relé, la bomba y el servo durante la carga por USB.
2. Conserva `config_local.py` y `calibracion_validada.json` en la placa; no los sustituyas por ejemplos.
3. Copia los módulos `.py` y la calibración de esta carpeta a la raíz del ESP32.
4. Inicia con la bomba desconectada del relé. Comprueba por telemetría `pump_active=false`, automatización desarmada y estado `LISTO`.
5. Prueba el servo sin croquetas y verifica las posiciones mecánicas. Prueba la bomba con el plato vacío y espacio suficiente; confirma que el relé se apague a los 5 s.
6. Habilita el modo automático desde la página solo cuando las pruebas manuales estén estables.

## Avisos sonoros

El buzzer pasivo de GPIO22 tiene secuencias no bloqueantes: un doble tono breve para la compuerta y tres notas ascendentes para el agua. Una falla de audio se registra sin cancelar por sí sola el control de la bomba o el servo.

## Verificación de software

`python -m unittest discover -s firmware/esp32_v2/tests -v` ejecuta la suite del firmware en la PC con salidas simuladas. No comprueba el cableado ni el movimiento físico.
