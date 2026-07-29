[CmdletBinding()]
param(
    [ValidateSet("User", "Process")]
    [string]$Scope = "User"
)

$secureToken = Read-Host "Collez le jeton Kaggle MCP commencant par KGAT" -AsSecureString
$tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
$plainToken = $null

try {
    $plainToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
    if (
        [string]::IsNullOrWhiteSpace($plainToken) -or
        -not $plainToken.StartsWith(
            "KGAT",
            [System.StringComparison]::Ordinal
        ) -or
        $plainToken.Length -lt 8 -or
        $plainToken -match "\s"
    ) {
        throw (
            "Jeton invalide : un jeton Kaggle MCP doit commencer par " +
            "KGAT et ne contenir aucun espace."
        )
    }

    [Environment]::SetEnvironmentVariable(
        "KAGGLE_MCP_TOKEN",
        $plainToken,
        [EnvironmentVariableTarget]::$Scope
    )
    if ($Scope -eq "User") {
        $env:KAGGLE_MCP_TOKEN = $plainToken
    }

    Write-Host (
        "KAGGLE_MCP_TOKEN configure dans l'environnement $Scope. " +
        "Le jeton n'a pas ete affiche ni ecrit dans le projet."
    )
    if ($Scope -eq "User") {
        Write-Host (
            "Redemarrez Codex Desktop pour que le connecteur Kaggle lise " +
            "la nouvelle variable."
        )
    }
}
finally {
    $plainToken = $null
    if ($tokenPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
    }
    $secureToken = $null
}
