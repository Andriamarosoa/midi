[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet(
        "configure", "pair", "probe", "sync-code", "sync-data",
        "bootstrap", "start", "stop", "status", "tail", "pull"
    )]
    [string]$Action,
    [string]$HostName,
    [string]$UserName,
    [int]$Port = 22,
    [string]$RemoteRoot,
    [string]$IdentityFile,
    [string]$LocalWorkspaceRoot,
    [string]$ConfigPath = "$PSScriptRoot\tmp\local\mac_worker.json",
    [string]$Manifest = "data\processed\polyphonic_harmonic_presence_v1\manifest_train_validation.csv",
    [string]$PythonBin = "python3.11",
    [string]$Module,
    [string[]]$ModuleArgs = @(),
    [ValidateSet("cpu", "metal")]
    [string]$Device = "metal",
    [string]$JobId,
    [ValidateRange(1, 22200)]
    [int]$WallTimeoutSeconds = 22200,
    [int]$Lines = 80,
    [string]$RunPath,
    [string]$Destination = "$PSScriptRoot\tmp\local\mac_results",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Utf8NoBom([string]$Path, [string]$Content) {
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Quote-Posix([string]$Value) {
    return "'" + $Value.Replace("'", "'`"'`"'") + "'"
}

function Assert-LastExit([string]$Operation) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

function Assert-RemoteRoot([string]$Value) {
    if (
        $Value -notmatch '^/[A-Za-z0-9._/-]+$' -or
        $Value -eq '/' -or
        (($Value -split '/') -contains '..') -or
        (($Value -split '/') -contains '.')
    ) {
        throw "remote_root must be a non-root absolute POSIX path without spaces or dot segments."
    }
}

function Load-WorkerConfig {
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Missing $ConfigPath. Run: .\MAC_WORKER.ps1 configure -HostName <mac> -UserName <user>"
    }
    $value = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
    if ($value.host -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
        throw "Invalid worker host in config."
    }
    if ($value.user -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
        throw "Invalid worker user in config."
    }
    Assert-RemoteRoot ([string]$value.remote_root)
    return $value
}

function Get-SshArguments($Config, [switch]$AllowPassword) {
    $arguments = @("-p", [string]$Config.port, "-o", "ConnectTimeout=10")
    if (-not $AllowPassword) {
        $arguments += @("-o", "BatchMode=yes")
    }
    if ($Config.identity_file) {
        $arguments += @("-i", [string]$Config.identity_file)
    }
    return $arguments
}

function Get-ScpArguments($Config) {
    $arguments = @("-P", [string]$Config.port, "-o", "ConnectTimeout=10", "-o", "BatchMode=yes")
    if ($Config.identity_file) {
        $arguments += @("-i", [string]$Config.identity_file)
    }
    return $arguments
}

function Get-SftpArguments($Config, [string]$BatchPath) {
    $arguments = @(
        "-b", $BatchPath,
        "-P", [string]$Config.port,
        "-o", "ConnectTimeout=10",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=6",
        "-o", "BatchMode=yes"
    )
    if ($Config.identity_file) {
        $arguments += @("-i", [string]$Config.identity_file)
    }
    return $arguments
}

function Quote-SftpPath([string]$Value) {
    if (
        $Value.Contains("`r") -or
        $Value.Contains("`n") -or
        $Value.Contains('"')
    ) {
        throw "Unsupported SFTP path character."
    }
    return '"' + $Value.Replace('\', '/') + '"'
}

function Assert-NoActiveSftp {
    $active = @(Get-Process -Name "sftp" -ErrorAction SilentlyContinue)
    if ($active.Count -gt 0) {
        $pids = ($active | ForEach-Object { $_.Id }) -join ","
        throw "Refusing a second SFTP upload while sftp.exe is active (PID $pids)."
    }
}

function Enter-SftpMutex {
    $mutex = New-Object System.Threading.Mutex(
        $false,
        "Local\MidiMacWorkerSftp"
    )
    $acquired = $false
    try {
        try {
            $acquired = $mutex.WaitOne(0)
        }
        catch [System.Threading.AbandonedMutexException] {
            $acquired = $true
        }
        if (-not $acquired) {
            throw "Another MAC_WORKER process owns the atomic SFTP mutex."
        }
        Assert-NoActiveSftp
        return $mutex
    }
    catch {
        if ($acquired) {
            try { $mutex.ReleaseMutex() } catch {}
        }
        $mutex.Dispose()
        throw
    }
}

function Exit-SftpMutex($Mutex) {
    try { $Mutex.ReleaseMutex() }
    finally { $Mutex.Dispose() }
}

function Invoke-SftpReput($Config, [string]$LocalPath, [string]$RemotePath) {
    $batchPath = Join-Path (
        Split-Path -Parent $LocalPath
    ) ("sftp-" + [guid]::NewGuid().ToString("N") + ".batch")
    $mutex = $null
    try {
        $mutex = Enter-SftpMutex
        $line = "reput -f " +
            (Quote-SftpPath ((Resolve-Path -LiteralPath $LocalPath).Path)) +
            " " + (Quote-SftpPath $RemotePath) + "`nquit`n"
        Write-Utf8NoBom $batchPath $line
        $arguments = Get-SftpArguments $Config $batchPath
        & sftp @arguments "$($Config.user)@$($Config.host)"
        Assert-LastExit "resumable SFTP upload"
    }
    finally {
        Remove-Item -LiteralPath $batchPath -Force -ErrorAction SilentlyContinue
        if ($null -ne $mutex) { Exit-SftpMutex $mutex }
    }
}

function Invoke-SftpPut($Config, [string]$LocalPath, [string]$RemotePath) {
    $batchPath = Join-Path (
        Split-Path -Parent $LocalPath
    ) ("sftp-" + [guid]::NewGuid().ToString("N") + ".batch")
    $mutex = $null
    try {
        $mutex = Enter-SftpMutex
        $line = "put -f " +
            (Quote-SftpPath ((Resolve-Path -LiteralPath $LocalPath).Path)) +
            " " + (Quote-SftpPath $RemotePath) + "`nquit`n"
        Write-Utf8NoBom $batchPath $line
        $arguments = Get-SftpArguments $Config $batchPath
        & sftp @arguments "$($Config.user)@$($Config.host)"
        Assert-LastExit "initial SFTP upload"
    }
    finally {
        Remove-Item -LiteralPath $batchPath -Force -ErrorAction SilentlyContinue
        if ($null -ne $mutex) { Exit-SftpMutex $mutex }
    }
}

function Invoke-Ssh($Config, [string]$Command, [switch]$AllowPassword) {
    $arguments = Get-SshArguments $Config -AllowPassword:$AllowPassword
    $target = "$($Config.user)@$($Config.host)"
    # Windows PowerShell 5.1 can split or strip quoting from a long native
    # command argument. Send one script through stdin instead. The trailing
    # comment safely absorbs the CRLF that PowerShell appends to the stream.
    $payload = $Command + "`n# mac-worker-stdin-terminator"
    $payload | & ssh @arguments $target bash -s
    Assert-LastExit "SSH command"
}

function Start-RemoteCaffeinate($Config) {
    $output = @(Invoke-Ssh $Config 'set -e; nohup /usr/bin/caffeinate -ims -t 21600 </dev/null >/dev/null 2>&1 & echo $!')
    $pidText = @($output | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ -match '^[0-9]+$' } | Select-Object -Last 1)
    if ($pidText.Count -ne 1) {
        throw "Remote caffeinate did not return one PID."
    }
    return [int]$pidText[0]
}

function Stop-RemoteCaffeinate($Config, [int]$CaffeinatePid) {
    $command = 'pid={0}; comm=$(ps -p "$pid" -o comm= 2>/dev/null | awk -F/ ''{{print $NF}}'' | tr -d '' ''); if [ "$comm" = caffeinate ]; then kill "$pid" 2>/dev/null || true; fi' -f $CaffeinatePid
    Invoke-Ssh $Config $command
}

function Initialize-RemoteUpload(
    $Config,
    [string]$RemoteArchive,
    [string]$ExpectedHash,
    [int64]$ExpectedSize
) {
    $remotePart = "$RemoteArchive.part"
    $remoteSidecar = "$remotePart.expected.env"
    $command = @(
        "set -euo pipefail",
        ("archive=" + (Quote-Posix $RemoteArchive)),
        ("part=" + (Quote-Posix $remotePart)),
        ("sidecar=" + (Quote-Posix $remoteSidecar)),
        ("expected_sha=" + (Quote-Posix $ExpectedHash)),
        ("expected_size=" + (Quote-Posix ([string]$ExpectedSize))),
        'if [ -e "$part" ] && [ ! -f "$sidecar" ]; then echo "Refusing orphan partial upload: $part" >&2; exit 20; fi',
        'if [ -e "$sidecar" ]; then test -f "$sidecar"; test "$(wc -l < "$sidecar" | tr -d '' '')" = 2; grep -Fxq "sha256=$expected_sha" "$sidecar"; grep -Fxq "size=$expected_size" "$sidecar"; else sidecar_tmp="$sidecar.tmp.$$"; umask 077; printf ''sha256=%s\nsize=%s\n'' "$expected_sha" "$expected_size" > "$sidecar_tmp"; mv "$sidecar_tmp" "$sidecar"; fi',
        'if [ -e "$part" ]; then test -f "$part"; partial_size=$(stat -f %z "$part"); test "$partial_size" -le "$expected_size"; if [ "$partial_size" = "$expected_size" ]; then partial_sha=$(shasum -a 256 "$part" | awk ''{print $1}''); test "$partial_sha" = "$expected_sha"; fi; fi',
        'if [ -e "$archive" ]; then test -f "$archive"; test ! -e "$part"; final_size=$(stat -f %z "$archive"); test "$final_size" = "$expected_size"; final_sha=$(shasum -a 256 "$archive" | awk ''{print $1}''); test "$final_sha" = "$expected_sha"; echo complete; elif [ -e "$part" ]; then if [ "$partial_size" = "$expected_size" ]; then echo complete; else echo resume; fi; else echo new; fi'
    ) -join "; "
    $output = @(Invoke-Ssh $Config $command)
    $state = @($output | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ -in @("complete", "new", "resume") } | Select-Object -Last 1)
    if ($state.Count -ne 1) {
        throw "Remote upload preparation returned no valid state."
    }
    return [string]$state[0]
}

function Complete-RemoteUpload(
    $Config,
    [string]$RemoteArchive,
    [string]$ExpectedHash,
    [int64]$ExpectedSize
) {
    $remotePart = "$RemoteArchive.part"
    $remoteSidecar = "$remotePart.expected.env"
    $command = @(
        "set -euo pipefail",
        ("archive=" + (Quote-Posix $RemoteArchive)),
        ("part=" + (Quote-Posix $remotePart)),
        ("sidecar=" + (Quote-Posix $remoteSidecar)),
        ("expected_sha=" + (Quote-Posix $ExpectedHash)),
        ("expected_size=" + (Quote-Posix ([string]$ExpectedSize))),
        'test -f "$sidecar"; test "$(wc -l < "$sidecar" | tr -d '' '')" = 2; grep -Fxq "sha256=$expected_sha" "$sidecar"; grep -Fxq "size=$expected_size" "$sidecar"',
        'if [ -e "$archive" ]; then test -f "$archive"; test ! -e "$part"; actual_size=$(stat -f %z "$archive"); actual_sha=$(shasum -a 256 "$archive" | awk ''{print $1}''); else test -f "$part"; actual_size=$(stat -f %z "$part"); test "$actual_size" = "$expected_size"; actual_sha=$(shasum -a 256 "$part" | awk ''{print $1}''); test "$actual_sha" = "$expected_sha"; mv "$part" "$archive"; fi',
        'test "$actual_size" = "$expected_size"',
        'test "$actual_sha" = "$expected_sha"'
    ) -join "; "
    Invoke-Ssh $Config $command
}

function Invoke-Worker($Config, [string[]]$Arguments) {
    $script = "$($Config.remote_root)/bin/mac_worker.sh"
    $quoted = @((Quote-Posix $script)) + ($Arguments | ForEach-Object { Quote-Posix ([string]$_) })
    Invoke-Ssh $Config ("bash " + ($quoted -join " "))
}

function Get-CurrentCommit([string]$Repository) {
    $commit = (& git -C $Repository rev-parse HEAD).Trim()
    Assert-LastExit "git rev-parse"
    if ($commit -notmatch '^[0-9a-f]{40}$') {
        throw "Git did not return a full commit SHA."
    }
    return $commit
}

function Assert-CleanRepository([string]$Repository) {
    $status = & git -C $Repository status --porcelain --untracked-files=all
    Assert-LastExit "git status"
    if ($status) {
        throw "The source worktree is dirty. Commit the coherent snapshot before synchronization.`n$status"
    }
}

if ($Action -eq "configure") {
    if (-not $HostName -or -not $UserName) {
        throw "configure requires -HostName and -UserName."
    }
    if (
        $HostName -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$' -or
        $UserName -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$'
    ) {
        throw "HostName/UserName contain unsupported characters."
    }
    if (-not $RemoteRoot) {
        $RemoteRoot = "/Users/$UserName/midi-worker"
    }
    Assert-RemoteRoot $RemoteRoot
    if (-not $LocalWorkspaceRoot) {
        $LocalWorkspaceRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
    }
    if (-not $IdentityFile) {
        $IdentityFile = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
    }
    $payload = [ordered]@{
        host = $HostName
        user = $UserName
        port = $Port
        remote_root = $RemoteRoot
        identity_file = $IdentityFile
        local_workspace_root = (Resolve-Path -LiteralPath $LocalWorkspaceRoot).Path
    }
    $parent = Split-Path -Parent $ConfigPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Write-Utf8NoBom $ConfigPath (($payload | ConvertTo-Json) + "`n")
    Write-Output "Configured local LAN worker: $UserName@$HostName ($RemoteRoot)"
    exit 0
}

$config = Load-WorkerConfig
$target = "$($config.user)@$($config.host)"
$repository = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$commit = Get-CurrentCommit $repository
if ($JobId -and $JobId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
    throw "JobId contains unsupported path characters."
}

if ($Action -eq "pair") {
    $keyPath = [string]$config.identity_file
    if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $keyPath) | Out-Null
        # Windows PowerShell 5.1 can drop a native empty-string argument and
        # make ssh-keygen consume -C as the passphrase. Passing a literal pair
        # of quotes through Start-Process preserves the intended empty value.
        $keygenArguments = @(
            "-t", "ed25519", "-f", $keyPath,
            "-N", '""', "-C", "midi-mac-worker"
        )
        $keygen = Start-Process `
            -FilePath (Get-Command ssh-keygen).Source `
            -ArgumentList $keygenArguments `
            -Wait -PassThru -NoNewWindow
        if ($keygen.ExitCode -ne 0) {
            throw "ssh-keygen failed with exit code $($keygen.ExitCode)."
        }
    }
    $publicKeyPath = "$keyPath.pub"
    if (-not (Test-Path -LiteralPath $publicKeyPath -PathType Leaf)) {
        throw "Missing public key: $publicKeyPath"
    }
    $command = 'umask 077; mkdir -p "$HOME/.ssh"; touch "$HOME/.ssh/authorized_keys"; key=$(cat); grep -qxF "$key" "$HOME/.ssh/authorized_keys" || printf "%s\n" "$key" >> "$HOME/.ssh/authorized_keys"'
    Get-Content -Raw -LiteralPath $publicKeyPath | & ssh @(Get-SshArguments $config -AllowPassword) $target $command
    Assert-LastExit "SSH key pairing"
    Write-Output "SSH key installed. Passwordless worker commands are now enabled."
    exit 0
}

if ($Action -eq "probe") {
    $root = Quote-Posix ([string]$config.remote_root)
    $command = "set -e; uname -m; sw_vers -productVersion; sysctl -n hw.memsize; df -h `$HOME; command -v python3.11 || true; test -d $root && echo worker_root=present || echo worker_root=missing"
    Invoke-Ssh $config $command
    exit 0
}

if ($Action -eq "sync-code") {
    Assert-CleanRepository $repository
    $temporaryRoot = Join-Path $repository "tmp\local"
    New-Item -ItemType Directory -Force -Path $temporaryRoot | Out-Null
    $archive = Join-Path $temporaryRoot "mac-code-$commit.tar"
    $buildingArchive = "$archive.building"
    $syncSucceeded = $false
    $caffeinatePid = $null
    try {
        if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
            Remove-Item -LiteralPath $buildingArchive -Force -ErrorAction SilentlyContinue
            & git -c core.autocrlf=false -C $repository archive --format=tar --output=$buildingArchive $commit
            Assert-LastExit "git archive"
            Move-Item -LiteralPath $buildingArchive -Destination $archive
        }
        $archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
        $archiveSize = (Get-Item -LiteralPath $archive).Length
        $runnerPath = Join-Path $repository "scripts/remote/mac_worker.sh"
        $runnerHash = (Get-FileHash -LiteralPath $runnerPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $remoteArchive = "$($config.remote_root)/inbox/mac-code-$commit.tar"
        $remotePart = "$remoteArchive.part"
        $remoteSidecar = "$remotePart.expected.env"
        Invoke-Ssh $config ("mkdir -p " + (Quote-Posix "$($config.remote_root)/inbox") + " " + (Quote-Posix "$($config.remote_root)/workspaces") + " " + (Quote-Posix "$($config.remote_root)/data"))
        $caffeinatePid = Start-RemoteCaffeinate $config
        $remoteState = Initialize-RemoteUpload $config $remoteArchive $archiveHash $archiveSize
        if ($remoteState -eq "new") {
            Invoke-SftpPut $config $archive $remotePart
        }
        elseif ($remoteState -eq "resume") {
            Invoke-SftpReput $config $archive $remotePart
        }
        Complete-RemoteUpload $config $remoteArchive $archiveHash $archiveSize

        $destination = "$($config.remote_root)/workspaces/$commit"
        $staging = "$($config.remote_root)/inbox/workspace-$commit"
        $sourceText = "commit=$commit`narchive_sha256=$archiveHash`n"
        $command = @(
            "set -euo pipefail",
            ("archive=" + (Quote-Posix $remoteArchive)),
            ("destination=" + (Quote-Posix $destination)),
            ("staging=" + (Quote-Posix $staging)),
            ("runner_source=" + (Quote-Posix "$destination/scripts/remote/mac_worker.sh")),
            ("runner_target=" + (Quote-Posix "$($config.remote_root)/bin/mac_worker.sh")),
            ("runner_tmp=" + (Quote-Posix "$($config.remote_root)/bin/mac_worker.sh.tmp")),
            ("sidecar=" + (Quote-Posix $remoteSidecar)),
            ('actual=$(shasum -a 256 "$archive" | awk ''{print $1}''); test "$actual" = ' + (Quote-Posix $archiveHash)),
            ('if [ -e "$destination" ]; then grep -Fxq ' + (Quote-Posix "commit=$commit") + ' "$destination/.source.env"; else rm -rf "$staging"; mkdir -p "$staging"; tar -xf "$archive" -C "$staging"; rm -rf "$staging/data"; ln -s ' + (Quote-Posix "$($config.remote_root)/data") + ' "$staging/data"; printf ' + (Quote-Posix $sourceText) + ' > "$staging/.source.env"; mv "$staging" "$destination"; fi'),
            ("mkdir -p " + (Quote-Posix "$($config.remote_root)/bin")),
            'rm -f "$runner_tmp"; tr -d ''\r'' < "$runner_source" > "$runner_tmp"',
            'bash -n "$runner_tmp"',
            ('actual_runner=$(shasum -a 256 "$runner_tmp" | awk ''{print $1}''); test "$actual_runner" = ' + (Quote-Posix $runnerHash)),
            'chmod 700 "$runner_tmp"; mv "$runner_tmp" "$runner_target"',
            'rm -f "$archive" "$sidecar"'
        ) -join "; "
        Invoke-Ssh $config $command
        $syncSucceeded = $true
        Write-Output "Code synchronized: commit=$commit archive_sha256=$archiveHash runner_sha256=$runnerHash"
    }
    finally {
        Remove-Item -LiteralPath $buildingArchive -Force -ErrorAction SilentlyContinue
        if ($null -ne $caffeinatePid) {
            try { Stop-RemoteCaffeinate $config $caffeinatePid }
            catch { Write-Warning "Could not stop remote caffeinate PID ${caffeinatePid}: $($_.Exception.Message)" }
        }
        if ($syncSucceeded) {
            Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
        }
        elseif (Test-Path -LiteralPath $archive -PathType Leaf) {
            Write-Warning "Archive preserved for exact SFTP resume: $archive"
        }
    }
    exit 0
}

if ($Action -eq "sync-data") {
    $localRoot = (Resolve-Path -LiteralPath ([string]$config.local_workspace_root)).Path.TrimEnd('\')
    $manifestPath = if ([System.IO.Path]::IsPathRooted($Manifest)) {
        (Resolve-Path -LiteralPath $Manifest).Path
    } else {
        (Resolve-Path -LiteralPath (Join-Path $localRoot $Manifest)).Path
    }
    $rows = @(Import-Csv -LiteralPath $manifestPath)
    if ($rows.Count -eq 0) { throw "Manifest is empty." }
    $splits = @($rows.split | Sort-Object -Unique)
    if (($splits -join ',') -ne 'train,validation') {
        throw "Only an exact train+validation manifest is allowed; found: $($splits -join ',')."
    }
    $manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $sourcePaths = @($manifestPath)
    foreach ($row in $rows) {
        foreach ($field in @("audio_path", "labels_path")) {
            if ($row.$field) { $sourcePaths += [string]$row.$field }
        }
    }
    $relativePaths = New-Object System.Collections.Generic.List[string]
    $totalBytes = [int64]0
    foreach ($source in ($sourcePaths | Sort-Object -Unique)) {
        $candidate = if ([System.IO.Path]::IsPathRooted($source)) {
            $source
        } else {
            Join-Path (Split-Path -Parent $manifestPath) $source
        }
        $resolved = (Resolve-Path -LiteralPath $candidate).Path
        if (-not $resolved.StartsWith($localRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing a manifest file outside local_workspace_root: $resolved"
        }
        $relative = $resolved.Substring($localRoot.Length + 1).Replace('\', '/')
        $relativePaths.Add($relative)
        $totalBytes += (Get-Item -LiteralPath $resolved).Length
    }
    if ($DryRun) {
        Write-Output "Data plan verified: rows=$($rows.Count) files=$($relativePaths.Count) bytes=$totalBytes manifest_sha256=$manifestHash splits=train,validation locked_test_used=false"
        exit 0
    }
    $temporaryRoot = Join-Path $localRoot "tmp\local"
    New-Item -ItemType Directory -Force -Path $temporaryRoot | Out-Null
    $listPath = Join-Path $temporaryRoot "mac-data-files.txt"
    $archive = Join-Path $temporaryRoot "mac-data-$manifestHash.tar"
    $buildingArchive = "$archive.building"
    $syncSucceeded = $false
    $caffeinatePid = $null
    try {
        Write-Utf8NoBom $listPath (($relativePaths -join "`n") + "`n")
        if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
            $drive = Get-PSDrive -Name ([System.IO.Path]::GetPathRoot($localRoot).Substring(0, 1))
            if ($drive.Free -lt ($totalBytes + 2GB)) {
                throw "Not enough temporary disk space for the $([math]::Round($totalBytes / 1GB, 2)) GiB LAN archive."
            }
            Remove-Item -LiteralPath $buildingArchive -Force -ErrorAction SilentlyContinue
            Push-Location $localRoot
            try {
                & tar -cf $buildingArchive -T $listPath
                Assert-LastExit "train/validation data archive"
            }
            finally { Pop-Location }
            Move-Item -LiteralPath $buildingArchive -Destination $archive
        }
        $archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
        $archiveSize = (Get-Item -LiteralPath $archive).Length
        $remoteArchive = "$($config.remote_root)/inbox/mac-data-$manifestHash.tar"
        $remotePart = "$remoteArchive.part"
        $remoteSidecar = "$remotePart.expected.env"
        Invoke-Ssh $config ("mkdir -p " + (Quote-Posix "$($config.remote_root)/inbox") + " " + (Quote-Posix "$($config.remote_root)/data"))
        $caffeinatePid = Start-RemoteCaffeinate $config
        $remoteState = Initialize-RemoteUpload $config $remoteArchive $archiveHash $archiveSize
        if ($remoteState -eq "new") {
            Invoke-SftpPut $config $archive $remotePart
        }
        elseif ($remoteState -eq "resume") {
            Invoke-SftpReput $config $archive $remotePart
        }
        Complete-RemoteUpload $config $remoteArchive $archiveHash $archiveSize
        Invoke-Worker $config @(
            "install-data", [string]$config.remote_root,
            $manifestHash, $archiveHash, [string]$rows.Count
        )
        Invoke-Ssh $config ("rm -f " + (Quote-Posix $remoteSidecar))
        $syncSucceeded = $true
        Write-Output "Data synchronized: rows=$($rows.Count) files=$($relativePaths.Count) bytes=$totalBytes manifest_sha256=$manifestHash archive_sha256=$archiveHash locked_test_used=false"
    }
    finally {
        Remove-Item -LiteralPath $buildingArchive -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $listPath -Force -ErrorAction SilentlyContinue
        if ($null -ne $caffeinatePid) {
            try { Stop-RemoteCaffeinate $config $caffeinatePid }
            catch { Write-Warning "Could not stop remote caffeinate PID ${caffeinatePid}: $($_.Exception.Message)" }
        }
        if ($syncSucceeded) {
            Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
        }
        elseif (Test-Path -LiteralPath $archive -PathType Leaf) {
            Write-Warning "Archive preserved for exact SFTP resume: $archive"
        }
    }
    exit 0
}

if ($Action -eq "bootstrap") {
    Invoke-Worker $config @("bootstrap", [string]$config.remote_root, $commit, $PythonBin)
    exit 0
}

if ($Action -eq "start") {
    if (-not $Module) { throw "start requires -Module." }
    if (-not $JobId) { $JobId = "job-" + (Get-Date -Format "yyyyMMdd-HHmmss") }
    Invoke-Worker $config (@(
        "start", [string]$config.remote_root, $commit, $JobId, $Device,
        [string]$WallTimeoutSeconds, $Module
    ) + $ModuleArgs)
    exit 0
}

if ($Action -eq "stop") {
    if (-not $JobId) { throw "stop requires -JobId." }
    Invoke-Worker $config @("stop", [string]$config.remote_root, $JobId)
    exit 0
}

if ($Action -eq "status") {
    $arguments = @("status", [string]$config.remote_root)
    if ($JobId) { $arguments += $JobId }
    Invoke-Worker $config $arguments
    exit 0
}

if ($Action -eq "tail") {
    if (-not $JobId) { throw "tail requires -JobId." }
    Invoke-Worker $config @("tail", [string]$config.remote_root, $JobId, [string]$Lines)
    exit 0
}

if ($Action -eq "pull") {
    if (-not $JobId) { throw "pull requires -JobId." }
    if (
        $RunPath -and (
            $RunPath -notmatch '^(runs|tmp)/[A-Za-z0-9._/-]+$' -or
            (($RunPath -split '/') -contains '..')
        )
    ) {
        throw "RunPath must be a relative runs/... or tmp/... path."
    }
    $destinationPath = Join-Path $Destination $JobId
    New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
    $scpArguments = Get-ScpArguments $config
    $statusText = (& ssh @(Get-SshArguments $config) $target ("cat " + (Quote-Posix "$($config.remote_root)/jobs/$JobId/status.env"))) -join "`n"
    Assert-LastExit "remote job status lookup"
    $jobCommit = (($statusText -split "`n") | Where-Object { $_ -match '^commit=' } | Select-Object -First 1) -replace '^commit=', ''
    if ($jobCommit -notmatch '^[0-9a-f]{40}$') {
        throw "Remote job status has no valid commit provenance."
    }
    foreach ($remote in @(
        "$($config.remote_root)/logs/$JobId.stdout.log",
        "$($config.remote_root)/logs/$JobId.stderr.log"
    )) {
        & scp @scpArguments "${target}:$remote" $destinationPath
        Assert-LastExit "job evidence download"
    }
    & scp @scpArguments -r "${target}:$($config.remote_root)/jobs/$JobId" $destinationPath
    Assert-LastExit "job state download"
    if ($RunPath) {
        $remoteRun = "$($config.remote_root)/workspaces/$jobCommit/$RunPath"
        & scp @scpArguments -r "${target}:$remoteRun" $destinationPath
        Assert-LastExit "run artifact download"
    }
    Get-ChildItem -LiteralPath $destinationPath -File -Recurse |
        Get-FileHash -Algorithm SHA256 |
        Select-Object Path, Hash
    exit 0
}
