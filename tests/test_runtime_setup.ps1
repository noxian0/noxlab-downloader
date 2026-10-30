$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\install-runtime.ps1')

function Assert-True($Condition, $Message) {
    if (-not $Condition) { throw $Message }
}

# Replace network and process operations so these tests never install software.
function Invoke-RestMethod {
    @(
        @{ version = 'v99.0.0'; lts = $false; files = @('win-x64-msi', 'win-arm64-msi') },
        @{ version = 'v24.1.0'; lts = 'LTS'; files = @('win-x64-msi', 'win-arm64-msi') },
        @{ version = 'v26.0.0'; lts = 'LTS'; files = @('win-x64-msi', 'win-arm64-msi') }
    )
}
function Invoke-WebRequest {
    if ($script:NetworkFails) { throw 'Network unavailable' }
}
function Get-AuthenticodeSignature {
    @{ Status = $script:SignatureStatus; SignerCertificate = @{ Subject = "CN=Test, O=$script:Publisher, C=US" } }
}
function Start-Process {
    param($FilePath, $ArgumentList, $WindowStyle, [switch]$Wait, [switch]$PassThru)
    $script:Launches += 1
    $script:LastArguments = $ArgumentList
    @{ ExitCode = $script:InstallerExit }
}

$script:NetworkFails = $false
$script:SignatureStatus = 'Valid'
$script:Publisher = 'Python Software Foundation'
$script:InstallerExit = 0
$script:Launches = 0
$node = Get-RuntimeDownload Node
Assert-True ($node.Url -like 'https://nodejs.org/dist/v26.0.0/*') 'Must select newest LTS, not a newer non-LTS release.'
Install-NoxlabRuntime Python
Assert-True ($script:Launches -eq 1) 'Python should launch once.'
Assert-True ($script:LastArguments -contains 'InstallAllUsers=0') 'Python must install for current user.'
Assert-True ($script:LastArguments -contains 'Include_tcltk=1') 'Python must include the GUI runtime.'

foreach ($scenario in @('BadSignature', 'WrongPublisher', 'Offline', 'Cancelled', 'InstallerError')) {
    $script:Launches = 0
    $script:Publisher = if ($scenario -eq 'WrongPublisher') { 'Someone else' } else { 'OpenJS Foundation' }
    $script:SignatureStatus = if ($scenario -eq 'BadSignature') { 'NotTrusted' } else { 'Valid' }
    $script:NetworkFails = $scenario -eq 'Offline'
    $script:InstallerExit = if ($scenario -eq 'Cancelled') { 1602 } else { 1603 }
    $failed = $false
    try { Install-NoxlabRuntime Node } catch { $failed = $true }
    Assert-True $failed "$scenario must report a failure."
    if ($scenario -in @('BadSignature', 'WrongPublisher', 'Offline')) {
        Assert-True ($script:Launches -eq 0) "$scenario must not launch an installer."
    }
}
$script:Publisher = 'OpenJS Foundation'
$script:SignatureStatus = 'Valid'
$script:NetworkFails = $false
$script:InstallerExit = 3010
Install-NoxlabRuntime Node
Assert-True ($script:LastArguments -contains '/norestart') 'Node installer must not restart Windows automatically.'

# Exercise setup's Python prompt/re-detection block without running pip or setup itself.
$setupPath = Join-Path $PSScriptRoot '..\setup.ps1'
$tokens = $null
$errors = $null
$tree = [Management.Automation.Language.Parser]::ParseFile($setupPath, [ref]$tokens, [ref]$errors)
Assert-True (-not $errors) 'Setup must parse on Windows PowerShell 5.1.'
$promptAst = $tree.Find({ param($ast)
    $ast -is [Management.Automation.Language.IfStatementAst] -and $ast.Extent.Text.StartsWith('if (-not $pythonInfo)')
}, $true)
$promptBlock = [scriptblock]::Create($promptAst.Extent.Text)
function Read-Host { return $script:Answer }
function Install-NoxlabRuntime { $script:PythonInstalls += 1 }
function Find-SupportedPython { return @{ Command = 'python.exe' } }
$originalPath = $env:Path
try {
    $script:Answer = 'n'
    $script:PythonInstalls = 0
    $pythonInfo = $null
    $cancelled = $false
    try { & $promptBlock } catch { $cancelled = $true }
    Assert-True ($cancelled -and $script:PythonInstalls -eq 0) 'Declining Python must stop setup without installing.'
    $script:Answer = ''
    . $promptBlock
    Assert-True ($script:PythonInstalls -eq 1 -and $pythonInfo.Command -eq 'python.exe') 'Accepting Python must install and re-detect before continuing.'
} finally {
    $env:Path = $originalPath
}
Write-Host 'Installer tests passed.'
