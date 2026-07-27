$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$run = Join-Path $PSScriptRoot "runs\polyphonic\polyphonic_v2_1_guitarset_gaps_20260720_001211"
$stateRoot = Join-Path $PSScriptRoot "runs\polyphonic\automation"
$stateLog = Join-Path $stateRoot "v2_pipeline_state.log"

Add-Content -LiteralPath $stateLog -Value "$(Get-Date -Format o) Resuming V2.1 from last.keras after interrupted epoch 9."
& $python -u -m src.polyphonic.train `
    --config configs\polyphonic_v2_1_guitarset_gaps.yaml `
    --resume-run $run
$exitCode = $LASTEXITCODE

@{
    finished_at = (Get-Date -Format o)
    exit_code = $exitCode
    resumed_run = $run
} | ConvertTo-Json | Set-Content `
    -LiteralPath (Join-Path $stateRoot "v2_1_finished.json") -Encoding UTF8

if ($exitCode -ne 0) {
    Add-Content -LiteralPath $stateLog -Value "$(Get-Date -Format o) Resumed V2.1 failed with exit code $exitCode."
    exit $exitCode
}
Add-Content -LiteralPath $stateLog -Value "$(Get-Date -Format o) Resumed V2.1 training complete."
