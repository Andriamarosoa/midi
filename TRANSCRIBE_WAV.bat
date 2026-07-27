@echo off
setlocal
cd /d "%~dp0"
if "%~2"=="" (
  echo Usage: TRANSCRIBE_WAV.bat entree.wav sortie.mid
  exit /b 2
)
".venv\Scripts\python.exe" -m src.product.transcribe "%~1" "%~2" --artifacts artifacts\guitar_midi_v1_0_0
