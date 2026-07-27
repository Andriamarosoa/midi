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
".venv\Scripts\python.exe" -m src.polyphonic.transcribe "%~1" "%~2" %3 %4 %5 %6 %7 %8 %9
endlocal
