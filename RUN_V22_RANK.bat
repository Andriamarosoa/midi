@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -u -m src.polyphonic.rank_checkpoints --run-dir "runs\polyphonic\polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644" --maximum-examples 60000 --checkpoint-glob "epochs/epoch-*.keras" 1>>"runs\polyphonic\v2_2_rank_60k.stdout.log" 2>>"runs\polyphonic\v2_2_rank_60k.stderr.log"
exit /b %errorlevel%
