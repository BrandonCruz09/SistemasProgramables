# Pruebas manuales del banco

Estas copias reúnen las pruebas del montaje. No sustituyen el programa integrado ni se guardan como `main.py`.
Pines vigentes: servo GPIO33, MOSFET GPIO23, báscula DT19/SCK18, DHT22 DATA4 y PIR OUT27.

1. Conectar por USB el ESP32 DevKit, no la cámara. Alimentación externa apagada mientras se cablea.
2. En Thonny abrir `prueba_componentes.py`; copiar también `banco_pesa.py`, `banco_sensores.py`, `banco_servo.py` y `hx711.py` al mismo directorio del dispositivo.
3. Ejecutar F5. Opción 1: RAW; 3: DHT22; 4: PIR; 5: servo; 6: lecturas conjuntas; 0: salir. Ctrl+C interrumpe una prueba y regresa al menú.
4. La lectura RAW funciona sin calibración. No son gramos. El factor y la tara deben medirse para convertir unidades.
5. Para observar un recorrido mayor sin carga, ejecutar por separado `identificar_giro_gpio33.py`: 1500 → 1000 → 2000 µs, dos ciclos y fin. No garantiza 180° ni permite giro continuo.
6. `prueba_bomba_gpio23.py` inicia SIG apagado, espera cinco segundos, envía un pulso de 0.8 s y termina apagado. La prueba confirmada fue del LED del módulo, SIN evidencia de bombeo.

El usuario ensayó localmente 800–3000 µs y reportó mayor recorrido. Esa copia local se conserva intacta; esta versión pública mantiene 1000–2000 µs hasta ajustar el mecanismo sin forzar topes.
No usar la carpeta de pruebas y la integrada a la vez: ambas contienen `hx711.py` y tienen objetivos distintos.
