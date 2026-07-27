@echo off
setlocal
cd /d "%~dp0\..\.."

set "COUNT=%~1"
if "%COUNT%"=="" set "COUNT=12"
set "RUNTIME=%~2"
if "%RUNTIME%"=="" set "RUNTIME=keras"
set "POLICY=%~3"
if "%POLICY%"=="" set "POLICY=current"
set "CAPTURE=%~4"
if "%CAPTURE%"=="" set "CAPTURE=normal"
set "MINIMUM_GAIN_DB=-12"
set "POLICY_SUFFIX="
if /I "%POLICY%"=="min0" (
  set "MINIMUM_GAIN_DB=0"
  set "POLICY_SUFFIX=_min0"
) else if /I not "%POLICY%"=="current" (
  echo Usage: %~nx0 [recordings] [keras^|tflite] [current^|min0] [normal^|weak12] 1>&2
  exit /b 2
)
set "CAPTURE_GAIN_DB=0"
set "CAPTURE_SUFFIX="
if /I "%CAPTURE%"=="weak12" (
  set "CAPTURE_GAIN_DB=-12"
  set "CAPTURE_SUFFIX=_weak12"
) else if /I not "%CAPTURE%"=="normal" (
  echo Usage: %~nx0 [recordings] [keras^|tflite] [current^|min0] [normal^|weak12] 1>&2
  exit /b 2
)
set "RUN=runs\polyphonic\polyphonic_v2_2_guitarset_gaps_guitar_techs_20260722_024644"
set "REPORT=%RUN%\reports\validation_live_input_level_v2_2_1_%RUNTIME%_%COUNT%%POLICY_SUFFIX%%CAPTURE_SUFFIX%.json"
set "STDOUT=%RUN%\v2_2_1_input_level_ab_%RUNTIME%_%COUNT%%POLICY_SUFFIX%%CAPTURE_SUFFIX%.stdout.log"
set "STDERR=%RUN%\v2_2_1_input_level_ab_%RUNTIME%_%COUNT%%POLICY_SUFFIX%%CAPTURE_SUFFIX%.stderr.log"

if exist "%REPORT%" (
  echo Validation report already exists; refusing to overwrite: "%REPORT%" 1>&2
  exit /b 3
)

".venv\Scripts\python.exe" -m src.polyphonic.validate_live_input_level ^
  --run-dir "%RUN%" ^
  --decoder-config "configs\polyphonic_live_decoder_v2_2_1.json" ^
  --maximum-recordings "%COUNT%" ^
  --runtime "%RUNTIME%" ^
  --artifacts "artifacts\guitar_midi_polyphonic_v2_2_0" ^
  --minimum-gain-db "%MINIMUM_GAIN_DB%" ^
  --capture-gain-db "%CAPTURE_GAIN_DB%" ^
  --output "%REPORT%" 1>"%STDOUT%" 2>"%STDERR%"

exit /b %errorlevel%
