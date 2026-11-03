@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero crea el entorno: py -3 -m venv .venv
  echo Despues instala: .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
".venv\Scripts\python.exe" descargar_modelo.py
if errorlevel 1 (
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -u vision_main.py
pause
