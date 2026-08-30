[CmdletBinding()]
param(
    [string]$RetiEmulator,
    [switch]$Dma,
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
    return $null
}

function Install-PicoOsTools {
    $DownloadScript = Join-Path $PSScriptRoot "download-tools.ps1"
    $Answer = Read-Host "RETI Emulator was not found. Download the latest RETI Emulator and PicoC Compiler? [y/N]"
    if ($Answer -notmatch "^(y|yes)$") {
        Write-Host "PicoOS tools were not downloaded"
        return $false
    }

    if (-not (Test-Path -LiteralPath $DownloadScript -PathType Leaf)) {
        throw "Download script not found: $DownloadScript"
    }

    if ([System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Unix) {
        & test -x $DownloadScript
        if ($LASTEXITCODE -ne 0) {
            & chmod +x $DownloadScript
            if ($LASTEXITCODE -ne 0) {
                throw "Could not make the download script executable: $DownloadScript"
            }
        }
    }

    & $DownloadScript
    return $true
}

$Emulator = Resolve-Tool `
    -ExplicitPath $RetiEmulator `
    -LocalNames @("reti_emulator.exe", "reti_emulator") `
    -CommandName "reti_emulator"

if (-not $Emulator) {
    if (-not (Install-PicoOsTools)) {
        exit 1
    }
    $Emulator = Resolve-Tool `
        -LocalNames @("reti_emulator.exe", "reti_emulator") `
        -CommandName "reti_emulator"
    if (-not $Emulator) {
        throw "The downloaded RETI Emulator was not found"
    }
}

$DmaArguments = if ($Dma) { @("--dma") } else { @() }
$Arguments = @(
    "-n", "5",
    "-e", "./boot/bootloader.reti",
    "-d", "-c", "-O",
    "-r", "262144",
    "-S", "kernel/kernel.sections",
    "-D", "kernel/kernel.debuginfo"
) + $DmaArguments + $EmulatorArguments

Push-Location $RuntimeRoot
try {
    & $Emulator @Arguments
    $Status = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $Status
