@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno Python. Consulta docs\FIREBASE_Y_SIMULACION.md.
  pause
  exit /b 1
)
if not exist "firebase_sim_config.json" (
  echo Falta firebase_sim_config.json. Copia el ejemplo y configura tu proyecto.
  pause
  exit /b 1
)
echo PetCare: prueba SIMULADA con Firebase real. No se controla hardware.
".venv\Scripts\python.exe" probar_firebase_mqtt.py
if errorlevel 1 (
  echo No se completo la prueba. Revisa configuracion y conexion a Internet.
) else (
  echo Prueba completada. Resultado en simulacion_resultado.json y en Firebase.
)
pause
