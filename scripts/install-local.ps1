param(
    [string]$Python = $env:PYTHON,
    [string]$VenvDir = $env:HSR_LOGIN_VENV_DIR,
    [string]$BinDir = $env:HSR_LOGIN_BIN_DIR
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AppName = "hsr-login"

if ([string]::IsNullOrWhiteSpace($Python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $Python = "py"
    } else {
        $Python = "python"
    }
}

if ([string]::IsNullOrWhiteSpace($VenvDir)) {
    $DataHome = $env:LOCALAPPDATA
    if ([string]::IsNullOrWhiteSpace($DataHome)) {
        $DataHome = Join-Path $HOME ".local\share"
    }
    $VenvDir = Join-Path $DataHome "$AppName\venv"
}

if ([string]::IsNullOrWhiteSpace($BinDir)) {
    $BinDir = Join-Path $HOME ".local\bin"
}

$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectDir = Resolve-Path (Join-Path $ScriptDir "..")

& $Python -m venv $VenvDir
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade $ProjectDir

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$PowerShellShim = Join-Path $BinDir "$AppName.ps1"
$CmdShim = Join-Path $BinDir "$AppName.cmd"
$ConsoleScript = Join-Path $VenvDir "Scripts\$AppName.exe"

@"
& '$ConsoleScript' @args
"@ | Set-Content -Encoding UTF8 -Path $PowerShellShim

@"
@echo off
"$ConsoleScript" %*
"@ | Set-Content -Encoding ASCII -Path $CmdShim

Write-Host "Installed $AppName to $BinDir"
Write-Host "If the command is not found, add $BinDir to PATH."
