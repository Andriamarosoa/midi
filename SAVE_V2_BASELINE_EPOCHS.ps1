param(
    [string]$Run = "runs\polyphonic\polyphonic_v2_0_guitarset_20260719_173445"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$runPath = Join-Path $PSScriptRoot $Run
$history = Join-Path $runPath "history.csv"
$last = Join-Path $runPath "last.keras"
$epochs = Join-Path $runPath "epochs"
New-Item -ItemType Directory -Force $epochs | Out-Null

function Save-LatestEpoch {
    if (-not (Test-Path $history) -or -not (Test-Path $last)) { return }
    $count = [Math]::Max(0, (Get-Content $history).Count - 1)
    if ($count -lt 1) { return }
    $target = Join-Path $epochs ("epoch-{0:D2}.keras" -f $count)
    if (-not (Test-Path $target)) {
        Copy-Item -LiteralPath $last -Destination $target
    }
}

while (-not (Test-Path (Join-Path $runPath "final.keras"))) {
    Save-LatestEpoch
    Start-Sleep -Seconds 20
}
Save-LatestEpoch
