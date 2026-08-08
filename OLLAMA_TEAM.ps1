[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("run", "benchmark", "models", "status")]
    [string]$Action,

    [string]$Role,
    [string]$Prompt,
    [string]$PromptFile,
    [string[]]$ContextFile = @(),
    [string[]]$Model = @(),
    [switch]$Json,
    [switch]$NoLog,
    [string]$ConfigPath = "$PSScriptRoot\tmp\local\mac_worker.json"
)

$ErrorActionPreference = "Stop"

function Quote-Posix([string]$Value) {
    return "'" + $Value.Replace("'", "'\''") + "'"
}

function Invoke-SshText([string]$RemoteCommand) {
    $arguments = @(
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=12",
        "-p", [string]$script:MacConfig.port
    )
    if ($script:MacConfig.identity_file) {
        $arguments += @("-i", [string]$script:MacConfig.identity_file)
    }
    $arguments += @(
        "$($script:MacConfig.user)@$($script:MacConfig.host)",
        $RemoteCommand
    )
    & ssh @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "SSH Ollama team command failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Missing ignored Mac config: $ConfigPath"
}
$script:MacConfig = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
foreach ($required in @("host", "user", "port", "remote_root")) {
    if (-not $script:MacConfig.$required) {
        throw "Mac config is missing '$required'."
    }
}

$remoteRepository = "/Users/$($script:MacConfig.user)/midi"
$remotePython = "$remoteRepository/scripts/local/ollama_team.py"
$remoteConfig = "$remoteRepository/configs/ollama_local_team.json"

if ($Action -in @("run", "benchmark")) {
    $localCommit = (& git -C $PSScriptRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $localCommit -notmatch "^[0-9a-f]{40}$") {
        throw "Cannot resolve the local Git commit."
    }
    $commitArguments = @(
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=12",
        "-p", [string]$script:MacConfig.port
    )
    if ($script:MacConfig.identity_file) {
        $commitArguments += @("-i", [string]$script:MacConfig.identity_file)
    }
    $commitArguments += @(
        "$($script:MacConfig.user)@$($script:MacConfig.host)",
        "git -C $(Quote-Posix $remoteRepository) rev-parse HEAD"
    )
    $remoteCommit = (& ssh @commitArguments).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Cannot resolve the remote Git commit."
    }
    if ($remoteCommit -ne $localCommit) {
        throw "Mac Git commit mismatch: expected $localCommit, got $remoteCommit. Pull the reviewed branch first."
    }
}

$command = "MIDI_MAC_WORKER_ROOT=$(Quote-Posix ([string]$script:MacConfig.remote_root)) " +
    "python3 $(Quote-Posix $remotePython) --config $(Quote-Posix $remoteConfig) "

if ($Action -eq "run") {
    if (-not $Role) {
        throw "-Role is required for run."
    }
    if ($Prompt -and $PromptFile) {
        throw "Use either -Prompt or -PromptFile, not both."
    }
    if ($PromptFile) {
        $Prompt = Get-Content -Raw -LiteralPath $PromptFile
    }
    if (-not $Prompt) {
        throw "A non-empty -Prompt or -PromptFile is required."
    }
    $promptBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Prompt))
    $command += "run --role $(Quote-Posix $Role) --prompt-base64 $(Quote-Posix $promptBase64)"
    foreach ($context in $ContextFile) {
        $command += " --context-file $(Quote-Posix $context)"
    }
    if ($Json) { $command += " --json" }
    if ($NoLog) { $command += " --no-log" }
} elseif ($Action -eq "benchmark") {
    $command += "benchmark"
    foreach ($modelName in $Model) {
        $command += " --model $(Quote-Posix $modelName)"
    }
} else {
    $command += $Action
}

Invoke-SshText $command
