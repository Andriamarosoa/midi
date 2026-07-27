@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Environnement .venv absent.
  exit /b 1
)
".venv\Scripts\python.exe" -m src.product.live --artifacts artifacts\guitar_midi_v1_0_0 %*
