# Integración MQTT e IA preparada el 8 de noviembre

Este documento amplía el corte inicial del mismo día. Ya existe código para:

`ESP32-CAM → JPEG por MQTT → PC OpenCV/MobileNet SSD → orden MQTT → RGB del ESP32 → ACK → Firebase`

También se conserva HTTP MJPEG para recuperar la configuración anterior. La IA se ejecuta en la PC. **La cadena nueva está probada por software, no cargada ni comprobada en ambas placas físicas.** El video y detección desde el celular sí fueron confirmados anteriormente usando HTTP.

## Qué se implementó

- `firmware/esp32cam/camara_mqtt.py`: JPEG binario, sin retención, reconexión y captura compartida con HTTP. Intervalo inicial 700 ms; socket con timeout de dos segundos. La frecuencia real depende de la cámara y red.
- `servidor/mqtt_camera.py`: recibe solo el último JPEG; rechaza imágenes retenidas, inválidas o mayores de 200 kB; una imagen sin renovar deja de considerarse disponible.
- `servidor/vision_main.py`: admite `camera_transport` igual a `http` o `mqtt`; mantiene página de video y modelo existentes.
- `servidor/ia_policy.py`: una señal por aparición confirmada de perro. Exige imagen reciente, detección no contradictoria y confianza mínima 0.60. Necesita tres cuadros sin perro para rearmarse y un mínimo de 15 segundos entre señales. No ordena comida ni agua.
- `servidor/mqtt_bridge.py`: entrada del puente. Publica `signal_dog` sin retención y relaciona su id con un ACK; registra `sin_confirmacion` si no recibe respuesta en cinco segundos. ACK significa orden aplicada por software, no medición física de luz.
- Firmware DevKit: `signal_dog` enciende RGB blanco durante 1.5 s y vuelve al indicador normal. No altera servo ni bomba. Los bloqueos de alimento sin calibración y bomba sin nivel permanecen.
- `firmware/lib/umqtt`: cliente oficial MicroPython incluido, con licencia y versión de origen. Copiarlo a `/lib/umqtt` en cada placa. Se corrigió el envío de identidad y credenciales como bytes.
- Firebase RTDB: rutas `lecturas`, `eventos_ia`, `estado_actual`, además de las anteriores. Telemetría actual por MQTT; histórico como máximo cada minuto salvo cambio de evento; una decisión conserva confianza, id y ACK.
- `interfaz/dashboard.html` y `servidor/dashboard.py`: estado, gráfica seleccionable, avisos de telemetría antigua, historial limitado y confirmaciones. Recupera hasta 120 registros de Firebase al iniciar si el servicio está configurado. Sin credenciales en el navegador ni botones de motores.
- `servidor/iniciar_integracion.py`: coordina broker, visión y puente. Ctrl+C cierra los procesos que abrió; no mata procesos ajenos si un puerto estaba ocupado.

## Tópicos y estado de Firebase

| Tópico | Contenido |
|---|---|
| petcare/equipo8/cam/frame | JPEG binario de la cámara, QoS0 y retain false |
| petcare/equipo8/vision | Resultado de IA, no imagen |
| petcare/equipo8/commands | Orden con id y action; IA usa signal_dog |
| petcare/equipo8/ack | Confirmación del programa de la placa |
| petcare/equipo8/telemetry | Lecturas, FSM y estado del indicador |

**Actualización posterior del mismo día:** la docente exige Cloud Firestore. Ya se creó en Spark, se publicaron reglas restringidas a la identidad de la PC y se activó el proveedor Firestore en el perfil privado. Pasaron 22 comprobaciones de integración con dispositivos simulados. RTDB queda como antecedente. [Detalle vigente](FIRESTORE_2026-11-08.md).

Las pruebas de nube del 8 de noviembre local aparecen con timestamp UTC del 9 de noviembre. No es evidencia del día siguiente: UTC y León tienen distinta fecha a esa hora.

## Preparación en esta computadora

Se dejó `PetCare_Listo_para_Probar` en el escritorio, fuera de Git, con:

- `ESP32`: programa integrado, calibración aún pendiente y MQTT configurado localmente.
- `ESP32CAM`: cámara existente más publicación MQTT, Wi-Fi privado conservado y base MB para cargar.
- `lib/umqtt` dentro de ambas carpetas.
- `INICIAR_PC.cmd`: inicio coordinado de la PC.

El perfil privado usa un broker con contraseña y ACL limitada a los tópicos de PetCare. No subir esta carpeta privada, configuraciones Wi-Fi, contraseñas, refresh tokens o archivos de autenticación. No reenviar puertos del router hacia Internet. La conexión MQTT es para la red local de confianza; no usa TLS.

Para otra computadora, copiar `server_config.example.json` como `server_mqtt_config.json`, completar broker/credenciales/IP, elegir MQTT y habilitar `automation.dog_indicator_enabled` y `dashboard.enabled`. Completar `mqtt_config.py` de cámara a partir del ejemplo. Configurar Mosquitto con usuario/contraseña y ACL; el archivo privado preparado no forma parte del repositorio.

## Prueba física pendiente

1. Preparar RGB de cátodo común: R a GPIO16 mediante 330 Ω, G a GPIO17 mediante 330 Ω, B a GPIO21 mediante 330 Ω y común a GND. Identificar patillas del componente, no adivinarlas. Si es un módulo, verificar tipo y resistencias incorporadas.
2. Dejar servo y bomba sin fuente para la primera demostración de IA. DevKit por USB. No modificar calibración ni puentear sensor de nivel para forzar motores.
3. Cargar por Thonny los archivos de la carpeta ESP32 a la DevKit, incluyendo `/lib/umqtt`; conservar respaldo de lo que había. Copiar main.py al final.
4. Cargar los de ESP32CAM a la cámara mediante su base MB, con `/lib/umqtt`. No borrar el flash ni reinstalar firmware: debe conservar el módulo camera que ya funcionaba. No mezclar programas de las dos placas.
5. Abrir `INICIAR_PC.cmd`. Ambas placas deben estar en el mismo Wi-Fi que la PC. Sus HOST apuntan a la IP LAN de la PC; solo el servidor PC usa 127.0.0.1. Si cambia la IP, actualizar los dos perfiles de placa.
6. Habilitar en Windows solo el acceso local a Mosquitto 1883 y Python 8765/8766. El helper del paquete solicita administrador; esa aprobación de Windows queda pendiente. No apagar todo el firewall.
7. Abrir el enlace de video que imprime la consola y el dashboard del puerto 8766 desde el celular. El panel debe mostrar telemetría reciente; sin calibración debe decir Sin calibrar, no gramos ficticios.
8. Colocar al perro frente a cámara fija. Tras confirmarse en varios cuadros debe aparecer el log de decisión y ACK, y RGB blanco durante 1.5 s. Retirar al perro al menos tres cuadros y esperar el intervalo antes de repetir. Grabar la secuencia sin cortes.
9. Capturar pantalla procesada, dashboard y log. Si no hay ACK en cinco segundos, revisar broker, Wi-Fi, suscripción, firmware y pines; no presentar el evento enviado como actuador comprobado.

El filtro reduce disparos repetidos pero no garantiza identificar correctamente todas las escenas. Medir falsos positivos y latencia con el encuadre real. Una demostración de LED no valida todavía la compuerta, gramos ni agua.

## Pruebas y límites

Se incluyen pruebas unitarias de FSM, cámara, IA, dashboard y cierres de salidas. `probar_cadena_mqtt.py` usa broker real y JPEG sintético; ejecuta además el modelo real sobre ese cuadro, pero inyecta el resultado dog para probar la decisión. No estima precisión del detector. `probar_firebase_mqtt.py` utiliza RTDB real y dispositivos simulados en una ruta aislada.

Resultados actuales: `PRUEBAS_SOFTWARE_INTEGRACION_2026-11-08.txt`, `PRUEBA_CADENA_MQTT_2026-11-08.json` y `PRUEBA_FIREBASE_2026-11-08.json`. Las pruebas no equivalen a una ejecución MicroPython real en las placas. La estructura de carpetas de la rúbrica aún requiere reconciliarse sin romper imports; no se presenta el reporte de avance como reporte final.

Fuente del cliente MicroPython: https://github.com/micropython/micropython-lib/tree/master/micropython/umqtt.simple

## Verificación de cierre de software

38 pruebas de software aprobadas, 12 comprobaciones de cadena MQTT local y 20 de Firebase real con dispositivos simulados. Se corrigió una espera de DNS inversa que bloqueaba el arranque de HTTP en Windows; ambos puertos 8765 y 8766 respondieron en la prueba de inicio y declararon datos físicos no disponibles. No se aplicaron permisos de administrador ni se cargaron placas. El PR existente y abierto es https://github.com/vetapia/SistemasProgramables/pull/5.
