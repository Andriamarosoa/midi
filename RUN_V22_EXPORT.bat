@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -u -m src.polyphonic.export --run-dir "runs\polyphonic\polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644" --output-dir "artifacts\guitar_midi_polyphonic_v2_2_0" --examples 96 1>>"runs\polyphonic\v2_2_export_fp16.stdout.log" 2>>"runs\polyphonic\v2_2_export_fp16.stderr.log"
exit /b %errorlevel%
