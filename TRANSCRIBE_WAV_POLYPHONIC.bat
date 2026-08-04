@echo off
setlocal
cd /d "%~dp0"
if "%~2"=="" (
  echo Usage: %~nx0 entree.wav sortie.mid [options]
  exit /b 2
)
if not exist ".venv\Scripts\python.exe" (
  echo Environnement .venv introuvable.
  exit /b 1
)
set "INPUT_WAV=%~1"
set "OUTPUT_MIDI=%~2"
shift
shift
".venv\Scripts\python.exe" -m src.polyphonic.transcribe "%INPUT_WAV%" "%OUTPUT_MIDI%" %*
endlocal
