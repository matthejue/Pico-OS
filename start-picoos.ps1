[CmdletBinding()]
param(
    [string]$RetiEmulator,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$EmulatorArguments
)

$ErrorActionPreference = "Stop"
$RuntimeRoot = $PSScriptRoot
$RepositoryRuntime = Join-Path $PSScriptRoot "binary\boot\bootloader.reti"
if (Test-Path -LiteralPath $RepositoryRuntime -PathType Leaf) {
    $RuntimeRoot = Join-Path $PSScriptRoot "binary"
}

function Resolve-Tool {
    param(
        [string]$ExplicitPath,
        [string[]]$LocalNames,
        [string]$CommandName
    )

    if ($ExplicitPath) {
        if (-not (Test-Path -LiteralPath $ExplicitPath -PathType Leaf)) {
            throw "Tool not found: $ExplicitPath"
        }
        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }

    foreach ($Root in @($RuntimeRoot, $PSScriptRoot)) {
        foreach ($Name in $LocalNames) {
            $Candidate = Join-Path $Root $Name
            if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
                return $Candidate
            }
        }
    }

    $Command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if ($Command) {
        return $Command.Source
    }
    throw "$CommandName was not found in the release directory or PATH. Run .\download-tools.ps1 to download the latest release"
}

$Emulator = Resolve-Tool `
    -ExplicitPath $RetiEmulator `
    -LocalNames @("reti_emulator.exe", "reti_emulator") `
    -CommandName "reti_emulator"

$Arguments = @(
    "-n", "5",
    "-e", "./boot/bootloader.reti",
    "-d", "-c", "-O",
    "-r", "262144",
    "-S", "kernel/kernel.sections",
    "-D", "kernel/kernel.debuginfo"
) + $EmulatorArguments

Push-Location $RuntimeRoot
try {
    & $Emulator @Arguments
    $Status = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $Status
