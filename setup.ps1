$ErrorActionPreference = "Stop"

$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$AppName = "NoxLab Downloader"
$VenvDir = Join-Path $ProjectRoot ".venv"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$GuiLauncher = Join-Path $ProjectRoot "NOXLAB_DOWNLOADER.pyw"
$CmdLauncher = Join-Path $ProjectRoot "noxdl.bat"
$IconPath = Join-Path $ProjectRoot "assets\noxlab_downloader_v3.ico"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Red
}

function Test-SupportedPython {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    try {
        $output = & $Command @Arguments -c "import sys; print(sys.executable); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            return [string]($output | Select-Object -Last 1)
        }
    }
    catch {
        return $null
    }
    return $null
}

function Find-SupportedPython {
    $candidates = @(
        @{ Command = "py"; Arguments = @("-3") },
        @{ Command = "python"; Arguments = @() }
    )

    foreach ($candidate in $candidates) {
        $python = Test-SupportedPython -Command $candidate.Command -Arguments $candidate.Arguments
        if ($python) {
            return @{
                Command = $candidate.Command
                Arguments = $candidate.Arguments
                Exe = $python
            }
        }
    }
    return $null
}

function New-AppShortcut {
    param(
        [string]$ShortcutPath,
        [string]$TargetPath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$IconLocation,
        [string]$Description
    )

    if (Test-Path -LiteralPath $ShortcutPath) {
        Remove-Item -LiteralPath $ShortcutPath -Force
    }

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.Arguments = $Arguments
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.IconLocation = "$IconLocation,0"
    $shortcut.Description = $Description
    $shortcut.Save()
}

Write-Step "Preparing NoxLab Downloader setup"

$pythonInfo = Find-SupportedPython
if (-not $pythonInfo) {
    throw "Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/ and enable Add python.exe to PATH."
}

Write-Step "Creating local virtual environment"
if (-not (Test-Path -LiteralPath $VenvDir)) {
    & $pythonInfo.Command @($pythonInfo.Arguments) -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPythonw = Join-Path $VenvDir "Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Virtual environment Python was not found at $VenvPython"
}
if (-not (Test-Path -LiteralPath $VenvPythonw)) {
    throw "Virtual environment pythonw.exe was not found at $VenvPythonw"
}

Write-Step "Installing required packages"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $Requirements

Write-Step "Checking app files"
if (-not (Test-Path -LiteralPath $GuiLauncher)) {
    throw "GUI launcher was not found at $GuiLauncher"
}
if (-not (Test-Path -LiteralPath $CmdLauncher)) {
    throw "Command launcher was not found at $CmdLauncher"
}
if (-not (Test-Path -LiteralPath $IconPath)) {
    throw "Shortcut icon was not found at $IconPath"
}

Write-Step "Creating downloads folder"
New-Item -ItemType Directory -Force (Join-Path $ProjectRoot "downloads") | Out-Null

Write-Step "Creating app shortcuts"
$Desktop = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = Join-Path $Desktop "$AppName.lnk"
$FolderShortcut = Join-Path $ProjectRoot "$AppName.lnk"
$ShortcutArgs = "`"$GuiLauncher`""

New-AppShortcut -ShortcutPath $DesktopShortcut -TargetPath $VenvPythonw -Arguments $ShortcutArgs -WorkingDirectory $ProjectRoot -IconLocation $IconPath -Description "Launch NoxLab Downloader"
New-AppShortcut -ShortcutPath $FolderShortcut -TargetPath $VenvPythonw -Arguments $ShortcutArgs -WorkingDirectory $ProjectRoot -IconLocation $IconPath -Description "Launch NoxLab Downloader"

Write-Host ""
Write-Host "NoxLab Downloader setup complete." -ForegroundColor Green
Write-Host "Desktop shortcut: $DesktopShortcut"
Write-Host "Folder shortcut:  $FolderShortcut"
Write-Host "The app shortcut opens the windowed downloader. Command prompt mode still works with noxdl.bat."
