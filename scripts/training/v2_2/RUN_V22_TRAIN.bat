@echo off
setlocal
cd /d "%~dp0\..\..\.."
set PYTHONUNBUFFERED=1
".venv\Scripts\python.exe" -u -m src.polyphonic.train --config configs\polyphonic_v2_2_guitarset_gaps_guitar_techs.yaml 1>>"runs\polyphonic\v2_2_train.stdout.log" 2>>"runs\polyphonic\v2_2_train.stderr.log"
exit /b %ERRORLEVEL%
