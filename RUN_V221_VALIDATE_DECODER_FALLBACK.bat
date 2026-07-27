@echo off
setlocal
cd /d "%~dp0"

set "COUNT=%~1"
if "%COUNT%"=="" set "COUNT=4"
set "RUN=runs\polyphonic\polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644"
set "REPORT=%RUN%\reports\validation_decoder_unattacked_threshold_v2_2_1_tflite_%COUNT%.json"
set "STDOUT=%RUN%\v2_2_1_decoder_unattacked_tflite_%COUNT%.stdout.log"
set "STDERR=%RUN%\v2_2_1_decoder_unattacked_tflite_%COUNT%.stderr.log"

if exist "%REPORT%" (
  echo Validation report already exists; refusing to overwrite: "%REPORT%" 1>&2
  exit /b 3
)

".venv\Scripts\python.exe" -m src.polyphonic.validate_live_input_level ^
  --run-dir "%RUN%" ^
  --decoder-config "configs\polyphonic_live_decoder_v2_2_1.json" ^
  --maximum-recordings "%COUNT%" ^
  --runtime tflite ^
  --artifacts "artifacts\guitar_midi_polyphonic_v2_2_0" ^
  --minimum-gain-db 0 ^
  --capture-gain-db 0 ^
  --output "%REPORT%" 1>"%STDOUT%" 2>"%STDERR%"

exit /b %errorlevel%
