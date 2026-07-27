@echo off
setlocal
cd /d "%~dp0\..\..\.."
".venv\Scripts\python.exe" -u -m src.polyphonic.select_final_checkpoint --run-dir "runs\polyphonic\polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644" --maximum-recordings 12 --maximum-candidates 8 1>>"runs\polyphonic\v2_2_select.stdout.log" 2>>"runs\polyphonic\v2_2_select.stderr.log"
exit /b %errorlevel%
