@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Environnement .venv introuvable.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m src.polyphonic.live %*
set "rc=%errorlevel%"
endlocal & exit /b %rc%
