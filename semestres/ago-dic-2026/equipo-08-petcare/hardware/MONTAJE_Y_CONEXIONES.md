# Montaje y conexiones al 8 de noviembre de 2026

La izquierda y derecha siempre se describen **mirando PetCare de frente, desde donde come el perro**. Comida a la izquierda, agua a la derecha. Las seis imágenes son ilustraciones de montaje propuesto, no fotografías del prototipo terminado, ni un esquemático validado ni plantillas de perforación a escala. Seguir nombres de terminales; no copiar filas del protoboard dibujado. Faltan medidas reales de módulos, platos y recipientes.

## Vista general y acercamientos

- [00 Vista general y caja abierta](montaje/00_vista_general.png)
- [01 Báscula y soporte](montaje/01_bascula.png)
- [02 Caja seca y distribución de alimentación](montaje/02_caja_seca.png)
- [03 Compuerta y servo MG995](montaje/03_servo.png)
- [04 Bomba y MOSFET](montaje/04_bomba.png)
- [05 Sensores cámara y resistencias](montaje/05_sensores.png)

La caja electrónica se fija a la izquierda del panel vertical, cerrada en el uso final, con tapa accesible. Los dibujos de detalle pueden omitir piezas para mostrar la zona: no cambian comida/agua de lado. El depósito azul y su compuerta quedan sobre el plato izquierdo. El depósito rojo y la manguera pertenecen a la zona derecha. Los soportes rígidos sostienen los recipientes; el coroplast es revestimiento y división, no una estructura portante validada.

## Alimentación

Trabajar desenchufado para cambiar cables. La fuente fotografiada tiene bornes de red accesibles: requiere cubierta adecuada, fijación y ubicación seca, fuera del alcance del perro y de salpicaduras. No montar la red eléctrica dentro de la zona del agua. La imagen no certifica su cableado actual.

La salida **V−** de la fuente es el retorno de baja tensión: unirla a GND del ESP32 y al retorno de las cargas. El símbolo de tierra de protección no sustituye a V− ni se usa como cable de retorno de sensores. No improvisar puentes en la entrada de red; su conexión de protección debe revisarla alguien competente.

| Origen | Destino | Observación |
|---|---|---|
| Fuente V+ 5 V | Bornera +5 V | Ramas independientes hacia servo y VIN del módulo MOSFET |
| Fuente V− | Bornera GND | GND ESP32, servo y módulo, referencia común |
| ESP32 USB | PC durante pruebas | No conectar además +5 V externo a VIN/5V mientras use USB sin aislamiento verificado |
| ESP32 3V3 | VCC HX711 y VCC DHT22 | No conectarlos al riel de motores de 5 V en esta guía |
| Fuente 5 V y V− | 5V y GND de ESP32-CAM en montaje autónomo | Confirmar placa; no alimentar simultáneamente USB/base MB y fuente externa |

La cámara se programa con su base MB. Se comunica por Wi-Fi con PC/celular; no necesita TX/RX hacia el otro ESP32. La alimentación autónoma del DevKit exige identificar su entrada 5V/VIN; nunca aplicar 5 V a 3V3. Mientras no esté identificada, mantenerlo por USB.

Usar borneras o conexiones firmes para la potencia. No transportar la corriente del servo o bomba por rieles del protoboard. Los rieles de protoboard pueden estar cortados a la mitad: confirmar continuidad antes de depender de ellos. Guiar señales por el borde seco y los pares rojo/negro de motores por otra ruta, sujetos con clips y con holgura en conexiones.

## Báscula y HX711

Debajo del plato izquierdo: base rígida → separador inferior → un extremo de la celda fijo. El extremo opuesto sostiene, con separador superior, la plataforma rígida del plato. La zona central de la celda queda libre. El plato y la plataforma no deben tocar la carcasa: ese apoyo desviaría la carga y falsearía la medida. No atornillar ambos extremos a la misma base.

| Conexión | Destino |
|---|---|
| HX711 VCC | ESP32 3V3 |
| HX711 GND | ESP32 GND |
| HX711 DT o DOUT | GPIO19 |
| HX711 SCK | GPIO18 |
| Celda rojo / negro | E+ / E−, respectivamente, si corresponde al modelo |
| Celda verde / blanco | A+ / A−, respectivamente, si corresponde al modelo |

Los colores de la celda son habituales, no universales. Conservar el cableado que ya produjo lecturas y verificar etiquetas/ficha antes de cambiarlo. Llevar sus cuatro hilos juntos, lejos de bomba/servo, con alivio de tensión; HX711 fijo sobre separadores en zona seca, sin cobre contra tornillos. El dibujo no permite deducir las medidas de los tornillos de tu celda.

RAW está probado según el equipo. Para gramos: montar la plataforma, tarar con el plato vacío, añadir una masa medida y calcular factor = (RAW con masa − tara) / masa en gramos. Luego comprobar con otra masa. Una botella marcada 1.5 L no proporciona por sí sola la masa exacta del conjunto. No inventar el factor ni bloquear la lectura RAW mientras falta calibración.

## Servo y compuerta

Rojo a +5 V externo; café/negro a V− común; naranja/amarillo a GPIO33. Sin resistencia en serie. Fijar cuerpo del MG995 a soporte rígido, no colgar del brazo el recipiente. La varilla acciona solo la compuerta; calibrar aperturas con pocas croquetas y detener si hace fuerza contra un tope. Borde flexible apto para contacto alimentario y salida ajustada reducen atascos, no los eliminan.

El MG995 posicional no se convierte por código en una rueda continua de 360°. Los valores 800–3000 µs fueron una prueba local del usuario; no están medidos como ángulos ni aprobados para carga. El código publicado conserva 50 Hz y 1000–2000 µs como rango inicial, sujeto a revisión del mecanismo. El programa integrado aún usa consignas heredadas; no afirmar que la compuerta final está calibrada.

## Bomba y módulo MOSFET

El detalle representa el módulo IRF520/IRF520N común. Confirmar modelo y serigrafía real: no basta la descripción verbal. Su LED encendido confirma señal, no la corriente disponible para mover la bomba. IRF520N no garantiza conducción suficiente con una señal de 3.3 V.

| Conexión | Terminal |
|---|---|
| GPIO23 | SIG del header |
| GND ESP32 | GND del header, unido a V− de fuente |
| +5 V fuente | VIN de potencia del módulo |
| V− fuente | GND de potencia del módulo |
| Bomba positivo | V+ de salida |
| Bomba negativo | V− de salida, NO puentearlo a GND |
| VCC del header | Sin conexión solo si se confirma el módulo común con VCC no usado; verificar placa |

Instalar un **1N4007** en paralelo con los cables de la bomba: franja al positivo, extremo sin franja al negativo. Esta selección se propone para minibomba de hasta 1 A; confirmar consumo. Aislar patas. Se requieren cable rojo/negro de potencia, propuesto 22 AWG para tramos cortos, y conexiones firmes. Bomba y diodo no se alimentan desde un GPIO.

Usar el depósito rojo con fondo cerrado, sin embudo abierto abajo. Sumergir la bomba solo si es un modelo sumergible. Tubo sale por arriba y su punta queda por encima del máximo nivel del depósito, con descarga libre dirigida al plato; comprobar que la bomba alcanza esa altura y no salpica. Verificar corte real de flujo al apagar. No introducir la punta bajo el agua del plato. El cable eléctrico forma un bucle bajo la entrada de la caja seca para que una gota no llegue por él al interior. Sensor de nivel pendiente: solo pruebas supervisadas, nunca bomba en seco.

## Sensores y resistencias

| Elemento | Conexión o cantidad | Condición |
|---|---|---|
| DHT22 módulo | VCC 3V3, GND, DATA GPIO4 | Seguir etiquetas, orden físico variable |
| Pull-up DHT22 | 1 resistencia 10 kΩ 1/4 W entre DATA y 3V3 | Solo si el módulo no la incorpora |
| PIR | OUT GPIO27, GND común, VCC según modelo | Su salida al ESP32 debe ser de 3.3 V como máximo |
| LED RGB cátodo común | R16, G17, B21, común GND | Confirmar tipo y patillas |
| Resistencias RGB | 3 de 330 Ω 1/4 W | Una en serie con cada color de LED suelto; confirmar si el módulo ya las trae |
| Flotador futuro | Contacto GPIO26 a GND, pull-up interno | Confirmar sentido al montar; no inyectar 5 V |
| Buzzer | GPIO22 como señal | Confirmar activo/pasivo, corriente y driver antes de conexión directa |
| HX711 y servo | Sin resistencia adicional en estas conexiones | No intercalar una resistencia para bajar su alimentación |

DHT22 ventilado en borde exterior seco; PIR hacia aproximación del perro, no encerrado; cámara alta mirando ambos platos, con separadores y lente despejada. Ajustar encuadre y región de interés una vez fija. Las etiquetas de piezas pendientes en las ilustraciones no son inventario confirmado: verificar lo que ya tienen antes de comprar.

## Referencias técnicas

- SparkFun, montaje y conexión de celda/HX711: https://learn.sparkfun.com/tutorials/load-cell-amplifier-hx711-breakout-hookup-guide/all?print=1
- Adafruit, conexión de DHT: https://learn.adafruit.com/dht/connecting-to-a-dhtxx-sensor
- Infineon, IRF520N: https://www.infineon.com/assets/row/public/documents/24/49/infineon-irf520n-datasheet-en.pdf
- Vishay, familia 1N4001 a 1N4007: https://www.vishay.com/docs/88503/1n4001.pdf

Ilustraciones generadas para explicar el montaje. Para el reporte final se requieren además fotos propias y un esquemático verificable. La lámina no sustituye la comprobación de etiquetas y continuidad en el hardware real.
