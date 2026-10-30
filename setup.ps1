$ErrorActionPreference = "Stop"

$ProjectRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$AppName = "NoxLab Downloader"
$VenvDir = Join-Path $ProjectRoot ".venv"
$Requirements = Join-Path $ProjectRoot "requirements.txt"
$GuiLauncher = Join-Path $ProjectRoot "NOXLAB_DOWNLOADER.pyw"
$CmdLauncher = Join-Path $ProjectRoot "noxdl.bat"
$IconPath = Join-Path $ProjectRoot "assets\noxlab_downloader_v3.ico"
$FfmpegDir = Join-Path $ProjectRoot "tools\ffmpeg"
$FfmpegBin = Join-Path $FfmpegDir "bin"
$FfmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
. (Join-Path $ProjectRoot "install-runtime.ps1")

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
        $output = & $Command @Arguments -c "import sys, tkinter, venv, ensurepip; print(sys.executable); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
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
    # Registered paths also work immediately after installation, before PATH refresh.
    $registered = foreach ($key in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore')) {
        foreach ($versionKey in (Get-ChildItem -LiteralPath $key -ErrorAction SilentlyContinue)) {
            $installKey = Get-Item -LiteralPath (Join-Path $versionKey.PSPath 'InstallPath') -ErrorAction SilentlyContinue
            if ($installKey) { Join-Path $installKey.GetValue('') 'python.exe' }
        }
    }
    $candidates = @(
        @{ Command = (Join-Path $VenvDir 'Scripts\python.exe'); Arguments = @() }
    ) + @($registered | ForEach-Object { @{ Command = $_; Arguments = @() } }) + @(
        @{ Command = "py"; Arguments = @("-3") },
        @{ Command = "python"; Arguments = @() }
    )

    foreach ($candidate in $candidates) {
        $resolvedCommand = Get-Command $candidate.Command -ErrorAction SilentlyContinue
        if (-not $resolvedCommand) { continue }
        if ($resolvedCommand.Source -like '*\Microsoft\WindowsApps\python.exe') { continue }
        $python = Test-SupportedPython -Command $candidate.Command -Arguments $candidate.Arguments
        if ($python) {
            return @{
                Command = $python
                Arguments = @()
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

function Test-FullFfmpeg {
    return (Test-Path -LiteralPath (Join-Path $FfmpegBin "ffmpeg.exe")) -and
        (Test-Path -LiteralPath (Join-Path $FfmpegBin "ffprobe.exe"))
}

function Install-FullFfmpeg {
    if (Test-FullFfmpeg) {
        Write-Host "Full FFmpeg is already installed." -ForegroundColor DarkGray
        return
    }

    Write-Step "Downloading full FFmpeg tools"
    Write-Host "Downloading FFmpeg Essentials (includes ffmpeg.exe and ffprobe.exe)..." -ForegroundColor DarkGray

    $TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "noxlab-ffmpeg-$PID"
    $ArchivePath = "$TempRoot.zip"
    try {
        New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
        Invoke-WebRequest -Uri $FfmpegUrl -OutFile $ArchivePath
        Expand-Archive -LiteralPath $ArchivePath -DestinationPath $TempRoot -Force

        $SourceFfmpeg = Get-ChildItem -LiteralPath $TempRoot -Filter "ffmpeg.exe" -File -Recurse |
            Where-Object { $_.Directory.Name -eq "bin" } |
            Select-Object -First 1
        if (-not $SourceFfmpeg) {
            throw "The downloaded FFmpeg archive did not contain ffmpeg.exe."
        }
        $SourceBin = $SourceFfmpeg.Directory.FullName
        $SourceFfprobe = Join-Path $SourceBin "ffprobe.exe"
        if (-not (Test-Path -LiteralPath $SourceFfprobe)) {
            throw "The downloaded FFmpeg archive did not contain ffprobe.exe."
        }

        if (Test-Path -LiteralPath $FfmpegDir) {
            Remove-Item -LiteralPath $FfmpegDir -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path $FfmpegBin | Out-Null
        Copy-Item -LiteralPath (Join-Path $SourceBin "ffmpeg.exe") -Destination $FfmpegBin -Force
        Copy-Item -LiteralPath $SourceFfprobe -Destination $FfmpegBin -Force

        $SourceRoot = [System.IO.Directory]::GetParent($SourceBin).FullName
        foreach ($Notice in @("LICENSE.txt", "README.txt")) {
            $NoticePath = Join-Path $SourceRoot $Notice
            if (Test-Path -LiteralPath $NoticePath) {
                Copy-Item -LiteralPath $NoticePath -Destination $FfmpegDir -Force
            }
        }

        & (Join-Path $FfmpegBin "ffmpeg.exe") -version | Select-Object -First 1
        if ($LASTEXITCODE -ne 0) {
            throw "The installed ffmpeg.exe tool could not be started."
        }
        & (Join-Path $FfmpegBin "ffprobe.exe") -version | Select-Object -First 1
        if ($LASTEXITCODE -ne 0) {
            throw "The installed ffprobe.exe tool could not be started."
        }
    }
    finally {
        Remove-Item -LiteralPath $ArchivePath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Step "Preparing NoxLab Downloader setup"

$pythonInfo = Find-SupportedPython
if (-not $pythonInfo) {
    Write-Host 'Python 3.10+ with Tkinter was not found. Setup can download and install Python 3.14 for you.'
    $answer = Read-Host 'Install Python from python.org now? [Y/n]'
    if ($answer -and $answer.Trim().ToLowerInvariant() -notin @('y', 'yes')) {
        throw 'Setup cancelled. Run setup.bat again when you are ready to install Python.'
    }
    Install-NoxlabRuntime -Name Python
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + $env:Path
    $pythonInfo = Find-SupportedPython
    if (-not $pythonInfo) { throw 'Python could not be detected after installation. Reopen setup.bat to retry.' }
}

Write-Step "Creating local virtual environment"
if (-not (Test-Path -LiteralPath $VenvDir)) {
    & $pythonInfo.Command @($pythonInfo.Arguments) -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local Python environment.' }
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
if ($LASTEXITCODE -ne 0) { throw 'Could not update pip. Check your internet connection and retry setup.' }
& $VenvPython -m pip install -r $Requirements
if ($LASTEXITCODE -ne 0) { throw 'Could not install the required packages. Check the error above and retry setup.' }

Install-FullFfmpeg

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
