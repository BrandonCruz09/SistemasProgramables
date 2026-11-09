# Plan de cierre del 8 al 15 de noviembre

> **Ampliación de software posterior a este corte:** ya se prepararon JPEG por MQTT, decisión IA con señal RGB, ACK, rutas de Firebase y dashboard. Pruebas de software y nube simulada aprobadas; carga y prueba física pendientes. [Estado actualizado y pasos](INTEGRACION_MQTT_IA.md).

Meta de trabajo: ensamblar y verificar lo existente para el 15 de noviembre de 2026. La indicación del curso admite el 30 como máximo; no usarlo para posponer la integración. El turno de demostración del equipo no está confirmado en este documento.

## Agenda propuesta

| Fecha | Trabajo | Evidencia para considerarlo terminado |
|---|---|---|
| 8 nov | Reunir código, HAL, imágenes y corte del avance en Git | Commit publicado y reporte con pendientes explícitos |
| 9 nov | Cerrar transporte requerido y decisión IA → MQTT → indicador | Captura procesada y log frame recibido → clase → comando → ack, con indicador físico visible |
| 10 nov | Enviar datos físicos y decisiones al servicio Firebase seleccionado | Lectura y devolución de registros con timestamp, sin mezclar simulaciones |
| 11 nov | Dashboard con estado actual, histórico y alertas | Captura con valores reales y comprobación de actualización; contrastar horario de demo con la docente |
| 12 nov | Tara/gramos; bomba con diodo; probar compuerta con croquetas | Medidas repetidas, volumen/tiempo, corte de flujo y registro de atascos |
| 13 nov | Fijar módulos, sujetar cables y cerrar carcasa | Fotos externas e internas, electrónica protegida, cámara encuadrada |
| 14 nov | Ensayo completo y reporte por secciones | Prueba sin cortes, recuperación ante fallas y conclusiones revisadas por cada integrante |
| 15 nov | Grabar y publicar video No listado; cerrar entrega | PDF, GitHub, video y revisión individual de la plataforma |

El calendario es una propuesta, no registro de actividades realizadas. Los roles por persona deben confirmarse; no asignar experiencias inventadas a Isaac o Lidia.

## Firebase y Firestore

Existe una implementación de **Realtime Database**, con evidencia previa de lecturas y escrituras reales para una ESP32 simulada y reglas limitadas a esa ruta. No existe evidencia de Firestore configurado. El texto nuevo usa Firebase y rutas tipo árbol, pero también dice colecciones: confirmar con la docente si exige específicamente Firestore. No migrar a ciegas ni activar facturación. Mantener la restricción de cero gasto y revisar cuotas del servicio elegido antes de habilitar hardware.

Para ajustarse al contenido solicitado, se propone esta correspondencia; **no está migrada ni validada todavía**:

| Ruta pedida | Origen actual | Información necesaria |
|---|---|---|
| lecturas/{timestamp} | telemetry/latest | Peso calibrado, temperatura, humedad, PIR, nivel y procedencia real/simulada |
| eventos_ia/{timestamp} | vision y eventos/ack | Clase, confianza, acción, id de comando, fecha y resultado de la ejecución |
| estado_actual | latest/vision | Últimos sensores, disponibilidad, estados y última actualización |

Las reglas actuales no autorizan datos físicos fuera del espacio simulado. Actualizarlas con autenticación y ámbito mínimo, sin lectura/escritura pública. La página de video actual no sustituye un dashboard con gráficas de Firebase. La confianza de la red no equivale a precisión medida. Deep Sleep solo si no impide responder a comandos; no es un requisito automático para este equipo alimentado por fuente.

## Diferencias de estructura que faltan resolver

| Rúbrica nueva | Ubicación actual | Acción pendiente |
|---|---|---|
| firmware/hal y firmware/main.py | firmware/esp32 con módulos y main.py | Reorganizar imports y despliegue; probar en placa después |
| firmware/cam | firmware/esp32cam | Alinear ruta y documentación sin perder firmware de cámara |
| servidor/ia | Módulos vision_* en servidor | Reorganizar y ejecutar pruebas de imports |
| servidor/mqtt_bridge.py | servidor/petcare_server.py | Adaptar punto de entrada documentado |
| servidor/requirements.txt | Existe | Congelar requisitos comprobados para la entrega |
| firebase/reglas.json y esquema.md | Archivos de reglas/esquema actuales | Alinear nombres y documentar servicio final sin publicar tokens |
| hardware/esquematico.png | Diagramas y guía de montaje | Crear/exportar esquemático Fritzing que pide esta rúbrica; no renombrar una ilustración como si lo fuera |
| hardware/carcasa.stl | No aplica al coroplast | Solo requerido si se imprime en 3D |
| docs/reporte_final.pdf | Avances y Word del corte | Ensamblar el reporte final cuando exista evidencia |

## Reporte final que se debe ensamblar

1. Portada e índice con integrantes y equipo 08.
2. Objetivo e infografía aprobada; no afirmar aprobación sin confirmación.
3. Materiales y tabla HAL actualizada con datos reales.
4. Marco teórico reutilizando tareas previas y citando fuentes.
5. Diagrama del sistema y conexiones, IA y Firebase incluidos.
6. Roles: cada integrante describe lo que realmente realizó.
7. Desarrollo de sensores/actuadores, IA, MQTT y Firebase, con código clave.
8. Resultados: fotos propias, capturas y enlace de YouTube.
9. Conclusión grupal y una individual por cada integrante, revisadas por sus autores.
10. Referencias en APA.

Este corte es material para ensamblar ese reporte, no la entrega final. Faltan evidencias y conclusiones individuales definitivas; no se rellenan con experiencias no confirmadas.

## Guion de video de hasta seis minutos

- 0:00–1:00: integrantes y problema; mostrar PetCare terminado.
- 1:00–2:30: explicar cámara → PC/OpenCV → MQTT y la decisión, con límites reales.
- 2:30–4:00: mostrar sensores, actuadores, Firebase y gráfica/estado actual.
- 4:00–5:00: prueba sensor → IA → actuador, en vivo y sin cortes.
- 5:00–6:00: reflexión de cada integrante, unos diez segundos por persona, y resultado.

Grabar horizontal, con voz clara, iluminación suficiente y sin música que tape la explicación. Publicar No listado y pegar el enlace en el reporte. Verificar enlace GitHub, protoboard oculto al exterior, encabezados en cada .py y conclusión individual de los tres integrantes. La entrega individual incluye el rol detallado y debe subirla cada persona.
