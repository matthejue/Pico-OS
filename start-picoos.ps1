[CmdletBinding()]
param(
    [string]$RetiEmulator,
    [Alias("M")]
    [switch]$Dma,
    [Alias("N", "notui")]
    [switch]$NoTui,
    [Alias("h")]
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$EmulatorArguments
)

$ErrorActionPreference = "Stop"
if ($Help) {
    $Usage = @(
        "Usage: .\start-picoos.ps1 [OPTIONS] [-- EMULATOR_ARGS...]",
        "",
        "Options:",
        "  -RetiEmulator PATH  Use a custom RETI Emulator executable",
        "  -Dma, -M            Enable DMA loading",
        "  -NoTui, -N          Start without the Debug TUI",
        "  -Help, -h           Show this help page",
        "  --                  Pass all following arguments to RETI Emulator"
    ) -join [Environment]::NewLine
    Write-Host $Usage
    exit 0
}

$NoTui = $NoTui -or ($EmulatorArguments -contains "--notui")
$EmulatorArguments = @($EmulatorArguments | Where-Object { $_ -ne "--notui" })
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

function Install-PicoOsTool {
    param(
        [string]$Tool,
        [string]$ToolName
    )

    $DownloadScript = Join-Path $PSScriptRoot "download-tools.ps1"
    $Answer = Read-Host "$ToolName was not found. Download the latest version? [y/N]"
    if ($Answer -notmatch "^(y|yes)$") {
        Write-Host "$ToolName was not downloaded"
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

    & $DownloadScript -Tool $Tool
    return $true
}

function Offer-PicoOsCheatsheet {
    $ArchiveReadme = Join-Path $RuntimeRoot "README.md"
    $CheatsheetName = "picoos-cheatsheet.pdf"
    $CheatsheetUrl = "https://github.com/matthejue/Pico-OS_Cheatsheet/releases/latest/download/$CheatsheetName"
    $CheatsheetFileLine = "More information can be found in ``$CheatsheetName`` in this archive directory."
    $CheatsheetLinkLine = "More information can be found under the following link: $CheatsheetUrl"

    if (-not (Test-Path -LiteralPath $ArchiveReadme -PathType Leaf)) {
        throw "Archive README not found: $ArchiveReadme"
    }
    $LastLine = Get-Content -LiteralPath $ArchiveReadme -Tail 1
    if ($LastLine -eq $CheatsheetFileLine -or $LastLine -eq $CheatsheetLinkLine) {
        return
    }

    $Answer = Read-Host "Download the latest PicoOS cheatsheet? [y/N]"
    if ($Answer -match "^(y|yes)$") {
        Invoke-WebRequest `
            -Uri $CheatsheetUrl `
            -OutFile (Join-Path $RuntimeRoot $CheatsheetName) `
            -UseBasicParsing
        $CheatsheetLine = $CheatsheetFileLine
    } else {
        $CheatsheetLine = $CheatsheetLinkLine
    }
    Add-Content -LiteralPath $ArchiveReadme -Value ""
    Add-Content -LiteralPath $ArchiveReadme -Value $CheatsheetLine
}

$Emulator = Resolve-Tool `
    -ExplicitPath $RetiEmulator `
    -LocalNames @("reti_emulator.exe", "reti_emulator") `
    -CommandName "reti_emulator"

if (-not $Emulator) {
    if (Install-PicoOsTool -Tool "reti_emulator" -ToolName "RETI Emulator") {
        $Emulator = Resolve-Tool `
            -LocalNames @("reti_emulator.exe", "reti_emulator") `
            -CommandName "reti_emulator"
    }
}

$Compiler = Resolve-Tool `
    -LocalNames @("picoc_compiler.exe", "picoc_compiler") `
    -CommandName "picoc_compiler"
if (-not $Compiler) {
    if (Install-PicoOsTool -Tool "picoc_compiler" -ToolName "PicoC Compiler") {
        $Compiler = Resolve-Tool `
            -LocalNames @("picoc_compiler.exe", "picoc_compiler") `
            -CommandName "picoc_compiler"
    }
}

if (-not $Emulator) {
    throw "RETI Emulator was not found"
}
if (-not $Compiler) {
    Write-Host "PicoC Compiler was not found"
}

Offer-PicoOsCheatsheet

if (-not $PSBoundParameters.ContainsKey("Dma")) {
    $Answer = Read-Host "Enable DMA? [y/N]"
    if ($Answer -match "^(y|yes)$") {
        $Dma = $true
    }
}

$DmaArguments = if ($Dma) { @("--dma") } else { @() }
$OptionsFile = Join-Path $RuntimeRoot "config\emulator_options.txt"
if (-not (Test-Path -LiteralPath $OptionsFile -PathType Leaf)) {
    throw "Emulator options file not found: $OptionsFile"
}
$DefaultArguments = (Get-Content -LiteralPath $OptionsFile -Raw).Trim() -split "\s+"
if ($NoTui) {
    $DefaultArguments = @($DefaultArguments | Where-Object { $_ -ne "-d" })
}
$Arguments = $DefaultArguments + $DmaArguments + $EmulatorArguments

Push-Location $RuntimeRoot
try {
    & $Emulator @Arguments
    $Status = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $Status
