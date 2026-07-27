param(
    [string]$BaselineRun = "runs\polyphonic\polyphonic_v2_0_guitarset_20260719_173445"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$baseline = Join-Path $PSScriptRoot $BaselineRun
$stateRoot = Join-Path $PSScriptRoot "runs\polyphonic\automation"
New-Item -ItemType Directory -Force $stateRoot | Out-Null

function Write-State([string]$message) {
    $line = "$(Get-Date -Format o) $message"
    Add-Content -LiteralPath (Join-Path $stateRoot "v2_pipeline_state.log") -Value $line
    Write-Output $line
}

Write-State "Waiting for baseline final.keras: $baseline"
while (-not (Test-Path (Join-Path $baseline "final.keras"))) {
    Start-Sleep -Seconds 30
}
Write-State "Baseline training complete. Running validation-only threshold selection."

if (-not (Test-Path (Join-Path $baseline "thresholds.json"))) {
    & $python -m src.polyphonic.evaluate_frames `
        --run-dir $baseline --split validation --select-thresholds
    if ($LASTEXITCODE -ne 0) { throw "Baseline frame validation failed." }
}

$eventReport = Join-Path $baseline "reports\validation_events.json"
if (-not (Test-Path $eventReport)) {
    & $python -m src.polyphonic.evaluate_events `
        --run-dir $baseline --split validation --maximum-recordings 12
    if ($LASTEXITCODE -ne 0) { throw "Baseline event validation failed." }
}

$started = Join-Path $stateRoot "v2_1_started.json"
if (Test-Path $started) {
    Write-State "V2.1 start sentinel already exists; no duplicate training launched."
    exit 0
}
@{
    started_at = (Get-Date -Format o)
    baseline = $baseline
    config = "configs\polyphonic_v2_1_guitarset_gaps.yaml"
} | ConvertTo-Json | Set-Content -LiteralPath $started -Encoding UTF8

Write-State "Starting full V2.1 GuitarSet+GAPS training."
& $python -m src.polyphonic.train `
    --config configs\polyphonic_v2_1_guitarset_gaps.yaml `
    --initial-checkpoint (Join-Path $baseline "best.keras")
$exitCode = $LASTEXITCODE
@{
    finished_at = (Get-Date -Format o)
    exit_code = $exitCode
    latest_run = if (Test-Path "runs\polyphonic\latest_run.txt") {
        Get-Content "runs\polyphonic\latest_run.txt" -Raw
    } else { $null }
} | ConvertTo-Json | Set-Content `
    -LiteralPath (Join-Path $stateRoot "v2_1_finished.json") -Encoding UTF8
if ($exitCode -ne 0) { throw "V2.1 training failed with exit code $exitCode." }
Write-State "V2.1 training complete. Final selection remains validation-only and manual."
