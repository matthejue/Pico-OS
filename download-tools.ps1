[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RuntimeRoot = $PSScriptRoot
$RepositoryRuntime = Join-Path $PSScriptRoot "binary\boot\bootloader.reti"
if (Test-Path -LiteralPath $RepositoryRuntime -PathType Leaf) {
    $RuntimeRoot = Join-Path $PSScriptRoot "binary"
}

$Architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
if ($Architecture -ne "X64") {
    throw "No PicoOS tool binaries are released for Windows $Architecture"
}

$TemporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("picoos-tools-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $TemporaryRoot | Out-Null

function Install-Package {
    param(
        [string]$Repository,
        [string]$Asset,
        [string]$ExecutableName
    )

    $Archive = Join-Path $TemporaryRoot $Asset
    $Extracted = Join-Path $TemporaryRoot ([System.IO.Path]::GetFileNameWithoutExtension($Asset))
    $Url = "https://github.com/matthejue/$Repository/releases/latest/download/$Asset"

    Write-Host "Downloading latest $Repository release..."
    Invoke-WebRequest -Uri $Url -OutFile $Archive -UseBasicParsing
    Expand-Archive -LiteralPath $Archive -DestinationPath $Extracted

    $Executable = Get-ChildItem -LiteralPath $Extracted -Recurse -File |
        Where-Object Name -EQ $ExecutableName |
        Select-Object -First 1
    if (-not $Executable) {
        throw "$Asset does not contain $ExecutableName"
    }

    $PackageRoot = $Executable.Directory.FullName
    Get-ChildItem -LiteralPath $PackageRoot -Recurse -File | ForEach-Object {
        $RelativePath = $_.FullName.Substring($PackageRoot.Length).TrimStart('\', '/')
        if ($RelativePath -ne "README.md") {
            $Destination = Join-Path $RuntimeRoot $RelativePath
            $DestinationDirectory = Split-Path -Parent $Destination
            New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $Destination -Force
        }
    }
}

try {
    Install-Package `
        -Repository "RETI-Emulator" `
        -Asset "reti-emulator-windows-x86_64.zip" `
        -ExecutableName "reti_emulator.exe"
    Install-Package `
        -Repository "PicoC-Compiler" `
        -Asset "picoc-compiler-windows-x86_64.zip" `
        -ExecutableName "picoc_compiler.exe"
} finally {
    Remove-Item -LiteralPath $TemporaryRoot -Recurse -Force
}

Write-Host "Installed the latest RETI Emulator and PicoC Compiler in $RuntimeRoot"
