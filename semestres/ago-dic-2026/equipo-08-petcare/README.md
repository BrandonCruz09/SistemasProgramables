# PetCare · Equipo 08

Dispensador supervisado de alimento y agua para perros. El sistema integra una ESP32 DevKit, una ESP32-CAM, una computadora con visión por computadora, un panel web local y Cloud Firestore.

**Video del proyecto:** [Ver en YouTube](https://youtu.be/n1oa04Dzscc)
**Repositorio:** [SistemasProgramables](https://github.com/BrandonCruz09/SistemasProgramables) · rama `ago-dic-2026/equipo-08`

## Funciones del sistema

- Muestra en gramos el peso del tazón desde la celda de carga y el HX711. La lógica de alimento usa como objetivo 300 g y supervisa el cierre de la compuerta.
- Controla la compuerta con un servo MG995. El panel permite abrir, cerrar y elegir una posición mediante un deslizador.
- Acciona la bomba mediante el relevador K1 durante un máximo configurado de 5 segundos por orden.
- Emite avisos con el buzzer pasivo y presenta las lecturas del DHT22 y del PIR.
- Recibe video de la ESP32-CAM por HTTP. El servidor de la PC procesa los cuadros con OpenCV y MobileNet-SSD.
- Comunica telemetría, órdenes y confirmaciones por MQTT. Registra lecturas y eventos seleccionados en Cloud Firestore.
- Ofrece control manual desde el navegador de la PC o de un teléfono conectado a la misma red local.

El modo automático por cámara inicia desarmado después de reiniciar y se habilita desde el panel. La detección de imagen informa presencia de perro/persona; la ejecución de órdenes queda bajo las reglas del firmware y del servidor.

## Arquitectura

```text
ESP32-CAM ──video HTTP/Wi-Fi──> PC: OpenCV + MobileNet-SSD ──> panel web
ESP32 DevKit <──MQTT──> PC: telemetría, órdenes y ACK
PC ──REST autenticado──> Cloud Firestore: estado, lecturas y eventos
Teléfono ──HTTP local──> panel servido por la PC
```

La ESP32-CAM y la DevKit son placas separadas. Consulta [arquitectura](hardware/arquitectura.png), [cableado de baja tensión](hardware/diagrama.png) y [tabla HAL](hardware/HAL.md) para ver las señales y responsabilidades de cada bloque.

## Componentes incluidos

ESP32 DevKit, ESP32-CAM OV2640, celda de carga con HX711, DHT22, PIR, servo MG995, relevador HW-383 K1, bomba de agua de 3–5 V, buzzer pasivo, diodo 1N4007, fuente regulada de 5 V, protoboard para señales, depósitos, manguera, tazones y carcasa. La versión final no usa LED RGB ni flotador; la pantalla OLED queda fuera de la integración documentada.

## Pines del firmware integrado

| Módulo | ESP32 DevKit | Función |
|---|---:|---|
| HX711 DOUT/DT | GPIO19 | Datos de peso |
| HX711 SCK | GPIO18 | Reloj del HX711 |
| DHT22 DATA | GPIO4 | Temperatura y humedad |
| PIR OUT | GPIO27 | Movimiento |
| Servo MG995 PWM | GPIO33 | Compuerta |
| Relevador K1 IN1 | GPIO23 | Bomba de agua; entrada activa en nivel bajo |
| Buzzer | GPIO22 | Avisos sonoros |

El factor y la tara que usa el firmware se guardan en `firmware/esp32_v2/calibracion_validada.json`. El firmware conserva esos valores al arrancar y comunica el peso en gramos. El servo opera a 50 Hz con los límites configurados en la tabla HAL.

## Estructura del repositorio

```text
firmware/esp32_v2/     Firmware integrado de la ESP32 DevKit
firmware/esp32cam/     Cámara OV2640 y conexión Wi-Fi/HTTP
firmware/lib/          Dependencias MicroPython incluidas
servidor/              Broker/puente MQTT, IA, panel y Firestore
interfaz/              HTML, CSS y JavaScript del panel
hardware/              HAL, diagramas y montaje
firebase/              Esquema y reglas de referencia
media/                 Evidencia visual del proyecto
docs/                 Reporte, guías y conclusiones individuales
```

El firmware integrado de la DevKit está en `firmware/esp32_v2/`. No combines módulos de carpetas de versiones anteriores. Los archivos `config_local.py`, credenciales del broker, tokens y perfiles reales permanecen locales y no se publican en GitHub.

## Preparar y ejecutar en la PC

Requisitos: Python 3 y los paquetes descritos en `servidor/requirements.txt`. Se necesita Mosquitto para MQTT; Firestore debe quedar configurado con credenciales locales de Firebase.

1. Instala dependencias desde la raíz del proyecto:

   ```powershell
   python -m pip install -r servidor/requirements.txt
   ```

2. En `servidor/`, crea los archivos locales a partir de los ejemplos: `server_mqtt_config.example.json`, `server_config.example.json`, `broker.local.conf.example` y `broker.acl.example`. Coloca la IP del equipo y las URL locales correspondientes. Conserva las credenciales fuera del repositorio.
3. En la ESP32 DevKit, carga los módulos de `firmware/esp32_v2/` y conserva `config_local.py` y `calibracion_validada.json` en la raíz de MicroPython. Carga el firmware de cámara desde `firmware/esp32cam/`.
4. Inicia broker, servidor de visión y panel desde la carpeta `servidor`:

   ```powershell
   python iniciar_integracion.py
   ```

5. Abre `http://127.0.0.1:8766/` en la PC. Para el teléfono, abre `http://IP_DE_LA_PC:8766/` en la misma red local. El visor de cámara usa el puerto `8765`.

La dirección de la PC y la URL de la cámara pueden cambiar al reconectarse al Wi-Fi; actualízalas en los perfiles locales antes de iniciar el servidor.

## Documentación de entrega

- [Tabla HAL](hardware/HAL.md)
- [Esquema de Cloud Firestore](firebase/esquema.md)
- [Reporte técnico final](docs/PetCare_Reporte_Tecnico_Final_25nov2026.docx)
- [Guía de arranque del reporte](docs/Guia_punto_partida_reporte_PetCare.docx)
- [Conclusión individual de Brandon](docs/PetCare_Conclusion_Individual_Brandon_23nov2026.docx)
- [Conclusión individual de Lidia](docs/PetCare_Conclusion_Individual_Lidia_23nov2026.docx)
- [Video del proyecto](https://youtu.be/n1oa04Dzscc)

Equipo 08 · Brandon Leonel Padilla De la Cruz (22240293), Isaac Eliseo Flores Valencia (22240324), Lidia Verenice Padilla López (22240312) · Sistemas Programables · ISC · TecNM León.\n