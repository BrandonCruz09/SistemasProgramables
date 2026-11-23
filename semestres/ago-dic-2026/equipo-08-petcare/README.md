# PetCare — Equipo 08

Dispensador supervisado de alimento y agua para perros, con báscula, sensores ambientales, cámara y panel local. El proyecto combina una ESP32 DevKit, una ESP32-CAM y servicios Python en una computadora.

## Estado para presentación

**Corte del software: 23 de noviembre de 2026.** La rama contiene el firmware integrado `petcare-23nov-r8`, el panel web y el servidor de visión/MQTT/Firestore. Las pruebas de software pasan; eso no certifica la báscula, el servo, la bomba ni la alimentación en el montaje final.

| Parte | Estado registrado | Límite pendiente |
|---|---|---|
| Firmware ESP32 | Versión r8 preparada; arranca con actuadores inactivos y automatización desarmada. | Hace falta cargar y confirmar el estado de la placa en cada sesión de presentación. |
| Báscula HX711 | Lee en gramos y conserva `calibracion_validada.json` sin volver a tarar al arrancar. | La referencia de 163 g fue declarada por el usuario, no verificada con una báscula independiente. El 21 de noviembre la última telemetría quedó en 36.46 g y después se volvió obsoleta; aún no se verificó que el peso cambie al caer croquetas. |
| Compuerta MG995 | GPIO33; extremos configurados 850–1500 µs. El panel ahora tiene deslizador para elegir posición intermedia; se conserva el cierre a 300 g, error de lectura o tiempo límite. | Probar el recorrido con la tapa montada y sin forzar el tope mecánico. Se reportó movimiento irregular al trabajar junto con la bomba. |
| Agua | Bomba por relé en GPIO23, pulso de 5 s y supervisión manual desde la página. | No mide mililitros ni nivel. Confirmar el corte real del flujo. |
| Cámara e IA | La ESP32-CAM entrega video por HTTP; la PC procesa cuadros con OpenCV y MobileNet-SSD para perro/persona. | La detección puede confundir perro y persona. Repetir la prueba en la carcasa y con el perro. |
| Firestore | El servidor Python usa Cloud Firestore mediante REST. Se guardaron eventos en verificaciones anteriores. | Las credenciales son locales y no están en Git. La conexión a la nube debe comprobarse al iniciar la presentación. |

**Resultado de pruebas del código en PC:** 141 pruebas del servidor y 64 del firmware simulado; también pasaron la revisión de sintaxis de JavaScript y `git diff --check`. No hubo prueba física integral en esta verificación. Al preparar este corte, el panel local no estaba ejecutándose y la ESP32 no tenía telemetría reciente.

## Cómo funciona

```text
ESP32-CAM ──video HTTP──> PC: OpenCV / detector ──> panel web del celular
ESP32 DevKit ──MQTT──> PC: panel, comandos y registro en Firestore
```

La cámara y la DevKit son placas separadas y se comunican con la PC por la red Wi‑Fi de 2.4 GHz. El panel acepta controles manuales. La automatización por cámara inicia desarmada y solo se activa desde el panel.

- **Croquetas:** la orden automática sirve por tandas hacia 300 g totales; se detiene ante falta de aumento de peso, error de lectura o límite de tiempo. Abrir manualmente mantiene el cierre supervisado por peso y por tiempo.
- **Agua:** cada orden supervisada activa la bomba hasta 5 s. El nivel y el volumen no se miden.
- **Buzzer:** emite un aviso corto al mover la compuerta y otro al iniciar el agua. El botón «Escuchar aviso» sirve para probarlo aparte.
- **Sensores:** DHT22, PIR y HX711. La OLED es opcional según que el módulo y el cableado coincidan con el display disponible.
- **Sin RGB ni flotador.**

## Mapa de pines del firmware

| Componente | ESP32 DevKit |
|---|---:|
| Servo MG995 | GPIO33 |
| Entrada del relé de la bomba | GPIO23 |
| Buzzer pasivo | GPIO22 |
| DHT22 DATA | GPIO4 |
| PIR OUT | GPIO27 |
| HX711 DOUT/DT | GPIO19 |
| HX711 SCK | GPIO18 |
| OLED SDA/SCL, si se instala | GPIO26 / GPIO25 |

El mapa de señales no certifica el cableado físico. Consulta [HAL](hardware/HAL.md) y [montaje y conexiones](hardware/MONTAJE_Y_CONEXIONES.md). No energices mientras cambias cables. La fuente del servo y la bomba necesita tierra común con la DevKit; no unas fuentes al riel de 5 V sin confirmar el esquema.

## Calibración de la báscula

El firmware utiliza el archivo `firmware/esp32_v2/calibracion_validada.json` con factor `285.80386` cuentas/g y tara `-8994.451`. El archivo indica que la masa de referencia de 163 g fue nominal y que el factor requiere validación con una masa medida independientemente. El programa no cambia la tara al arrancar. No copies valores de básculas de otras carpetas o pruebas antiguas.

Para servir alimento, el tazón debe descansar únicamente sobre la plataforma de la celda; no debe tocar la carcasa y sus cables no deben tensarlo. Si la lectura no está fresca o la celda falla, el firmware bloquea el servido o solicita cerrar la compuerta.

## Archivos principales

```text
firmware/esp32_v2/    Firmware integrado para la ESP32 DevKit
firmware/esp32cam/    Código de la cámara OV2640 y ejemplos de configuración
servidor/             Dashboard, MQTT, OpenCV, detector y Firestore REST
interfaz/             HTML, CSS y JavaScript del panel
hardware/HAL.md       Pines, tópicos y unidades
hardware/             Referencias de conexión y montaje
docs/                 Reportes, evidencia y bitácoras históricas
```

Para la carga actual se utiliza `firmware/esp32_v2/`. Las carpetas `firmware/esp32/` y `firmware/esp32cam/` contienen versiones y utilidades de otras etapas; no mezcles archivos de pruebas antiguas con el firmware integrado.

## Preparación y ejecución

1. Instala Python y las dependencias en la PC:

   ```powershell
   python -m pip install -r servidor/requirements.txt
   ```

2. En `servidor/`, copia `server_mqtt_config.example.json` a `server_mqtt_config.json`. Cambia usuario y contraseña MQTT, IP LAN de la PC y URL de la cámara. Instala Mosquitto y ajusta `mosquitto_exe`. Configura Firestore solo si ya preparaste el proyecto y las credenciales locales; el ejemplo lo deja apagado. Copia `broker.local.conf.example` a `broker.local.conf`, cambia las dos rutas de Windows y ajusta `broker.acl.example` al usuario elegido. Crea `broker.passwd` con `mosquitto_passwd`; no escribas la contraseña en el archivo de configuración. En la ESP32 DevKit y la ESP32-CAM crea los archivos locales de Wi‑Fi/MQTT desde sus ejemplos. Ningún archivo local con contraseñas o tokens se versiona.

3. En Thonny, conecta la DevKit con las cargas externas apagadas y copia los módulos `.py` de `firmware/esp32_v2/` y `calibracion_validada.json` a la raíz de la placa. Conserva el `config_local.py` privado que ya está en ella. Verifica la versión y el estado inactivo antes de conectar la bomba o el servo.

4. Configura la ESP32-CAM con su firmware que incluye soporte para OV2640 y los archivos de `firmware/esp32cam/`. La URL de cámara se indica en el perfil privado del servidor; no es fija y puede cambiar al reconectar al Wi‑Fi.

5. Inicia el broker, la visión y el panel desde la carpeta `servidor`:

   ```powershell
   python iniciar_integracion.py
   ```

   El panel queda en `http://127.0.0.1:8766/` en la PC; desde el celular usa la dirección IP de la PC y el mismo puerto. El visor de cámara usa el puerto 8765. El servidor, la cámara y la DevKit deben estar en la misma red local de 2.4 GHz; ajusta las direcciones del ejemplo a la red real.

6. Antes de armar el modo automático, comprueba que la página muestre una lectura reciente, el video y el estado correcto de los sensores. Prueba el servo y el relé por separado y confirma físicamente que la compuerta cierre y que el agua se corte.

## Pruebas reproducibles

Desde la raíz de PetCare, en PowerShell:

```powershell
python -m unittest discover -s servidor -p "test_*.py" -v
python -m unittest discover -s firmware/esp32_v2/tests -p "test_*.py" -v
node --check interfaz/assets/dashboard.js
git diff --check
```

Las pruebas usan dobles de sensores, actuadores y servicios. No confirman el movimiento real del MG995, el flujo de la bomba, la exactitud de la calibración ni la detección del perro en el montaje final.

## Repositorio

Equipo 08 · Sistemas Programables · ISC, TecNM León
Repositorio: [SistemasProgramables](https://github.com/BrandonCruz09/SistemasProgramables)
Rama de trabajo: `ago-dic-2026/equipo-08`
