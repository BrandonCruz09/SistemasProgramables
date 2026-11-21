# Interfaz local PetCare

El panel de control está en `dashboard.html`, con estilos y lógica en `assets/dashboard.css` y `assets/dashboard.js`. Se sirve desde `servidor/petcare_server.py` cuando `dashboard.enabled` está activo, normalmente en el puerto 8766. El puente MQTT debe estar conectado para que los botones lleguen al ESP32.

El video de cámara se carga desde el servidor de visión, normalmente en el puerto 8765. La cámara puede seguir transmitiendo aunque el panel esté cerrado.

La automatización por cámara permanece desarmada al iniciar. El panel solicita habilitarla y espera confirmación del ESP32; solo entonces el servidor de IA publica señales que pueden iniciar el servido. Reiniciar el servidor deja de publicar esas señales; reiniciar el ESP32 desarma también el controlador de la placa.
