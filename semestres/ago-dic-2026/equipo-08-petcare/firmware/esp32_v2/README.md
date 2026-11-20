# PetCare r4 del 19 de noviembre

Integra PetCare_v2_19nov_r2.zip con las correcciones de errores de r3. Revisión preparada y probada en PC. La carga al ESP32 y la comprobación física siguen pendientes: Windows no detecta un puerto serie. El apagado físico de la bomba reportado por el usuario todavía no se ha comprobado.

## Manual y automático

Manual: comida, compuerta, agua y buzzer desde el panel. feed completa hasta 300 g totales; gate_open mantiene la apertura con corte a 300 g. gate_test_open es solo para pruebas sin croquetas y requiere cierre manual.

Automático autorizado: signal_dog llega desde una detección confirmada de perro en la PC. Con peso válido inferior a 20 g solicita comida hasta 300 g. Solicita agua durante 5 segundos después del alimento si hay servido en curso. Si falla la pesa, no inicia comida; el agua puede funcionar independientemente.

Pausas automáticas: 4 horas para comida y 2 horas para agua. Un servido manual inicia la pausa automática correspondiente, pero los botones manuales siguen disponibles. Entre pulsos de agua hay al menos 10 segundos de espera en firmware. Las pausas son en RAM y se reinician al apagar o reiniciar la placa.

La solicitud de agua pendiente caduca a los 120 segundos. Detener agua, cancelar alimento, un fallo de control o deshabilitar la automatización la descartan. No hay flotador ni medición de volumen: 5 segundos no son 500 ml comprobados. Mantener supervisión y comprobar capacidad del plato.

## GPIO y posiciones

Servo GPIO33 a 50 Hz: abrir 1350 µs y cerrar 1690 µs, manteniendo PWM. No se incorporaron 800 ni 3000 µs. main.py ordena cerrar al arrancar; solo_lectura=True y la prueba independiente no mueven el servo al iniciar.

Relé IN1 GPIO23 activo LOW, máximo 5000 ms, con temporizador y comprobación de plazo en el bucle. Buzzer pasivo GPIO22, DHT22 GPIO4, PIR GPIO27, HX711 DT19/SCK18, OLED SDA26/SCL25. Sin RGB ni flotador. Un ACK o GPIO lógico no demuestra clic, giro o flujo.

## Calibración

Se incorporó el archivo del ZIP: factor 285.80386 cuentas/g y tara -8994.451, correspondiente al cero documentado en ../../docs/PRUEBA_CERO_18NOV.txt. La tara anterior -428929.16 sigue identificada en el JSON y respaldada antes de integrar. No se recalibró físicamente ni se midió una masa nueva. El factor original usó un paquete nominal de 163 g; la precisión actual debe comprobarse con carga conocida. No hay tara automática al arrancar.

El control usa la mediana de las tres últimas muestras para rechazar picos aislados. La pantalla usa hasta cinco muestras. Una lectura inválida o antigua solicita el cierre del alimento.

## Instalación y prueba

1. Fuente externa desenchufada durante la carga. ESP32 normal por USB, sin +5 V externo en VIN.
2. Respaldar la placa, sobre todo config_local.py y los JSON de calibración.
3. Copiar juntos los .py y calibracion_validada.json de esta carpeta a la raíz de la placa. Conservar config_local.py; no reemplazarlo por el ejemplo. No mezclar con ../esp32, que es histórico.
4. En la PC usar servidor/ia_policy.py y el perfil real con automation.dog_indicator_enabled=true. Los perfiles locales ya se actualizaron, sin publicar sus contraseñas. Reiniciar el servidor después de preparar cámara, broker y red.
5. Thonny, prueba_servo.py: F5 abre el menú; 1 abre, 2 cierra, 0 sale. No hay ciclos automáticos. prueba_bomba.py prueba el relé por separado. Detener una prueba antes de iniciar otra.
6. Verificar cierre físico y corte del agua a los 5 segundos antes de poner main.py en servicio. Bomba sumergida, manguera al plato y espacio para recibir agua. Si no se apaga, desenchufar la fuente y no repetir pulsos.
7. Comprobar tazón vacío y carga conocida; después probar alimento hasta 300 g con supervisión.

La ESP32-CAM no requiere cambios de GPIO ni firmware por esta integración. La cámara y la detección real siguen pendientes en esta sesión.

## Resultados

ZIP original: 41 pruebas aprobadas. Integración: 61 pruebas de firmware y 29 de panel, ACK, IA/MQTT y Firestore en PC con servicios simulados. Incluyen política de perro a MQTT y controlador, corte a 300 g, agua a 5 s, cancelaciones, duplicados y fallos. No son ensayos eléctricos ni escrituras nuevas en Firestore real.

Desde la raíz del proyecto: python -m unittest discover -s firmware/esp32_v2/tests -v
Desde servidor: python -m unittest test_ack_estado test_dashboard test_firestore test_ia_mqtt -v

Sin PC, la cola de agua conserva eventos recientes y cuenta los descartados en water_events_dropped. No bloquea el agua manual por falta de espacio en la cola.
