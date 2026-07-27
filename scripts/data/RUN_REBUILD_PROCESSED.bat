@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist "runs\data" mkdir "runs\data"
".venv\Scripts\python.exe" scripts\data\rebuild_processed.py --workers 4 1>"runs\data\rebuild_processed.stdout.log" 2>"runs\data\rebuild_processed.stderr.log"
exit /b %errorlevel%
