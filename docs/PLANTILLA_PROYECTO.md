# [Nombre del Proyecto]

![Estado](https://img.shields.io/badge/estado-en--desarrollo-yellow)
![Semestre](https://img.shields.io/badge/semestre-ago--dic--2026-blue)
![Materia](https://img.shields.io/badge/materia-Sistemas%20Programables-orange)

> **Semestre:** ago-dic-2026
> **Materia:** Sistemas Programables — ISC TecNM León
> **Integrantes:**

| Nombre | Matrícula | Rol | GitHub |
|--------|-----------|-----|--------|
| Estudiante 1 | L00000000 | 🔧 Firmware ESP32 | @usuario |
| Estudiante 2 | L00000000 | 🧠 Servidor Python/IA | @usuario |
| Estudiante 3 | L00000000 | ☁️ Firebase/Interfaz | @usuario |
| Estudiante 4 | L00000000 | 🔩 Hardware/Carcasa | @usuario |
| Estudiante 5 | L00000000 | 📝 Documentación | @usuario |

---

## 📌 Descripción General

Explica en 2–3 oraciones:
- ¿A quién ayuda este proyecto?
- ¿Qué problema resuelve?
- ¿Cómo lo resuelve de forma diferente a lo que ya existe?

---

## 🏗️ Arquitectura del Sistema

> 📌 **Inserta aquí tu diagrama de arquitectura como imagen.**
> No uses texto — coloca una imagen que muestre el flujo completo de tu sistema.
> Guárdala en `hardware/` y actualiza la ruta abajo.

![Arquitectura del sistema](hardware/arquitectura.png)

### Tópicos MQTT

| Tópico | Dirección | Descripción |
|--------|-----------|-------------|
| `proyecto/sensor1` | ESP32 → Broker | Lectura sensor 1 |
| `proyecto/sensor2` | ESP32 → Broker | Lectura sensor 2 |
| `proyecto/sensor3` | ESP32 → Broker | Lectura sensor 3 |
| `proyecto/cam/frame` | ESP32-CAM → Broker | Frame de cámara |
| `proyecto/actuador1/cmd` | Broker → ESP32 | Comando actuador 1 |
| `proyecto/actuador2/cmd` | Broker → ESP32 | Comando actuador 2 |
| `proyecto/actuador3/cmd` | Broker → ESP32 | Comando actuador 3 |

---

## 🛠️ Hardware

| # | Componente | Tipo | Cantidad | Costo aprox. MXN |
|---|-----------|------|----------|-----------------|
| 1 | ESP32 DevKit | Microcontrolador | 1 | $120 |
| 2 | ESP32-CAM | Cámara | 1 | $130 |
| 3 | _Sensor 1_ | Sensor | 1 | |
| 4 | _Sensor 2_ | Sensor | 1 | |
| 5 | _Sensor 3_ | Sensor | 1 | |
| 6 | _Actuador 1_ | Actuador | 1 | |
| 7 | _Actuador 2_ | Actuador | 1 | |
| 8 | _Actuador 3_ | Actuador | 1 | |
| 9 | _Componente estrella_ | No convencional | 1 | |
| **Total** | | | | **< $800 MXN** |

### Diagrama de conexiones

> Inserta aquí una imagen que muestre cómo están conectados los componentes.
> Puede ser un diagrama hecho en cualquier herramienta (Fritzing, draw.io, Canva, foto del circuito, etc.).
> Guarda la imagen en `hardware/` y actualiza la ruta abajo.

![Diagrama de conexiones](hardware/diagrama.png)

---

## 💻 Software y Firmware

### Requisitos del servidor Python

```bash
pip install -r servidor/requirements.txt
```

### Cómo ejecutar el sistema completo

**1. Levantar el broker MQTT** (en una terminal aparte):
```
mosquitto
```

**2. Cargar firmware en la ESP32:**
Abrir Thonny → conectar la ESP32 → cargar los archivos de `firmware/` desde la interfaz gráfica.

**3. Ejecutar el servidor de IA:**
```
cd servidor
python mqtt_bridge.py
```

### Librerías ESP32 (MicroPython — corren en la placa)

| Librería | Uso |
|---------|-----|
| `umqtt.simple` | Cliente MQTT en la ESP32 |
| `machine` | Control de pines GPIO |
| `network` | Conexión WiFi |
| _otras según proyecto_ | |

### Librerías servidor Python (corren en la PC)

| Librería | Versión | Uso |
|---------|---------|-----|
| paho-mqtt | ≥ 1.6 | Cliente MQTT en el servidor |
| opencv-python | ≥ 4.8 | Procesamiento de imagen |
| firebase-admin | ≥ 6.0 | Escritura en Firestore |
| _librería IA_ | x.x | _modelo usado_ |

---

## 🧠 Inteligencia Artificial

- **Modelo:** _(OpenCV / MediaPipe / TensorFlow Lite / otro)_
- **Qué detecta:** _(descripción de la tarea de clasificación o detección)_
- **Cómo toma decisiones:** _(lógica: si detecta X → publica cmd Y)_
- **Confianza mínima aceptada:** _%_

---

## 🎥 Demostración

**Video demostrativo (YouTube):** [▶️ Ver video](https://youtube.com/watch?v=XXXXXXXX)

### Fotos del prototipo final

| Vista frontal | Vista interna | Sistema en operación |
|--------------|---------------|----------------------|
| ![frontal](media/prototipo-frontal.jpg) | ![interna](media/prototipo-interno.jpg) | ![operacion](media/sistema-operacion.jpg) |

---

## 📋 HAL — Hardware Abstraction Layer

| # | Componente | Pin ESP32 | Tópico MQTT | Unidad | Rango válido |
|---|-----------|-----------|-------------|--------|-------------|
| 1 | Sensor 1 | GPIO__ | proyecto/s1 | | |
| 2 | Sensor 2 | GPIO__ | proyecto/s2 | | |
| 3 | Sensor 3 | GPIO__ | proyecto/s3 | | |
| 4 | Actuador 1 | GPIO__ | proyecto/a1/cmd | | |
| 5 | Actuador 2 | GPIO__ | proyecto/a2/cmd | | |
| 6 | Actuador 3 | GPIO__ | proyecto/a3/cmd | | |

---

## 🔥 Esquema Firebase

```
/nombre-proyecto/
  /lecturas/{timestamp}/
      sensor1: valor
      sensor2: valor
      sensor3: valor
  /eventos_ia/{timestamp}/
      deteccion: "clase"
      accion: "actuador_ON"
      confianza: 0.92
  /estado_actual/
      sensor1: ultimo_valor
      actuador1: "ON"
```

---

## ⚠️ Retos técnicos encontrados

_(Llenar al finalizar el proyecto — esta sección alimenta las conclusiones del reporte)_

1.
2.
3.

---

*Sistemas Programables · ISC TecNM León · ago-dic-2026*
