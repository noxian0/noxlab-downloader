param(
    [ValidateSet('Python', 'Node')]
    [string]$Runtime
)

function Get-RuntimeDownload {
    param([ValidateSet('Python', 'Node')][string]$Name)

    $architecture = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
    $arch = switch ($architecture) {
        'AMD64' { 'x64' }
        'ARM64' { 'arm64' }
        default { throw 'The automatic installer requires 64-bit Windows (x64 or ARM64).' }
    }
    if ($Name -eq 'Python') {
        $version = '3.14.10'
        $suffix = if ($arch -eq 'x64') { 'amd64' } else { 'arm64' }
        return @{
            Url = "https://www.python.org/ftp/python/$version/python-$version-$suffix.exe"
            FileName = "python-$version-$suffix.exe"
            Publisher = 'Python Software Foundation'
        }
    }

    $releases = Invoke-RestMethod -Uri 'https://nodejs.org/dist/index.json' -TimeoutSec 60
    $release = $releases | Where-Object { $_.lts -and $_.files -contains "win-$arch-msi" } |
        Sort-Object { [version]($_.version.TrimStart('v')) } -Descending | Select-Object -First 1
    if (-not $release -or $release.version -notmatch '^v\d+\.\d+\.\d+$') {
        throw 'Could not find a supported Node.js LTS installer.'
    }
    $fileName = "node-$($release.version)-$arch.msi"
    return @{
        Url = "https://nodejs.org/dist/$($release.version)/$fileName"
        FileName = $fileName
        Publisher = 'OpenJS Foundation'
    }
}

function Assert-RuntimeSignature {
    param([string]$Path, [string]$Publisher)
    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike "*O=$Publisher,*") {
        throw "Installer signature could not be verified for $Publisher. Installation stopped."
    }
}

function Install-NoxlabRuntime {
    param([ValidateSet('Python', 'Node')][string]$Name)
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $download = Get-RuntimeDownload -Name $Name
    $tempDir = Join-Path ([IO.Path]::GetTempPath()) ("noxlab-runtime-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    $installer = Join-Path $tempDir $download.FileName
    try {
        Write-Host "Downloading $($download.FileName) from $([uri]$download.Url | Select-Object -ExpandProperty Host)..."
        Invoke-WebRequest -UseBasicParsing -Uri $download.Url -OutFile $installer -TimeoutSec 600
        Assert-RuntimeSignature -Path $installer -Publisher $download.Publisher
        if ($Name -eq 'Python') {
            Write-Host 'Installing Python for your Windows account...'
            $process = Start-Process -FilePath $installer -ArgumentList @(
                '/passive', '/norestart', 'InstallAllUsers=0', 'PrependPath=1',
                'Include_pip=1', 'Include_tcltk=1', 'Include_launcher=0', 'Include_test=0'
            ) -WindowStyle Hidden -Wait -PassThru
        } else {
            Write-Host 'Complete the Node.js installer window, then return to NoxLab Downloader.'
            # This is an interactive installer; Windows handles any elevation prompt.
            $process = Start-Process -FilePath "$env:SystemRoot\System32\msiexec.exe" -ArgumentList @(
                '/i', ('"' + $installer + '"'), '/norestart'
            ) -WindowStyle Normal -Wait -PassThru
        }
        if ($process.ExitCode -eq 1602) { throw "$Name installation was cancelled." }
        if ($process.ExitCode -notin @(0, 3010)) { throw "$Name installer failed (exit code $($process.ExitCode))." }
        if ($process.ExitCode -eq 3010) { Write-Host 'Windows reports that a restart is required to finish installation.' }
        Write-Host "$Name installer completed."
    } finally {
        # Remove only the installer file created by this invocation, then its empty folder.
        if (Test-Path -LiteralPath $installer) { Remove-Item -LiteralPath $installer -Force }
        Remove-Item -LiteralPath $tempDir -ErrorAction SilentlyContinue
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        if (-not $Runtime) { throw 'Specify -Runtime Python or -Runtime Node.' }
        Install-NoxlabRuntime -Name $Runtime
        exit 0
    } catch {
        Write-Host "Installation failed: $($_.Exception.Message)"
        exit 1
    }
}
