<#
    build_release.ps1 - build JustDownloadIT and its Inno Setup installer.

    Packaging only: this script does not modify application code, UI or the
    download logic. It produces an onedir PyInstaller bundle (no UPX, no
    onefile) and then compiles installer.iss with Inno Setup.

    Usage (from this folder):
        powershell -ExecutionPolicy Bypass -File .\build_release.ps1

    Output:
        release_build\dist\JustDownloadIT\   (onedir bundle)
        installer_output\JustDownloadIT-Setup.exe
#>

$ErrorActionPreference = 'Stop'

$Root         = $PSScriptRoot
$SpecPath     = Join-Path $Root 'JustDownloadIT.spec'
$IssPath      = Join-Path $Root 'installer.iss'
$DistPath     = Join-Path $Root 'release_build\dist'
$WorkPath     = Join-Path $Root 'release_build\build'
$BundleDir    = Join-Path $DistPath 'JustDownloadIT'
$InstallerDir = Join-Path $Root 'installer_output'
$InstallerExe = Join-Path $InstallerDir 'JustDownloadIT-Setup.exe'

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "BUILD STOPPED: $Message" -ForegroundColor Red
    Write-Host ""
    exit 1
}

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

Write-Host "JustDownloadIT release build" -ForegroundColor White

# ---------- 1. Prerequisite: Python ----------
Write-Step "Checking for Python"
$Python = $null
foreach ($candidate in @('python', 'py')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            & $cmd.Source --version *> $null
            if ($LASTEXITCODE -eq 0) { $Python = $cmd.Source; break }
        } catch { }
    }
}
if (-not $Python) {
    Fail "Python was not found on PATH. Install Python 3.8+ (https://www.python.org/downloads/) and make sure it is on PATH, then re-run this script."
}
Write-Host "    Python: $Python"

# ---------- 2. Prerequisite: PyInstaller ----------
Write-Step "Checking for PyInstaller"
try {
    $pyiVersion = (& $Python -m PyInstaller --version) 2>&1
    if ($LASTEXITCODE -ne 0) { throw 'nonzero exit' }
} catch {
    Fail "PyInstaller is not available for this Python. Install it with:  $Python -m pip install pyinstaller  - then re-run this script."
}
Write-Host "    PyInstaller: $pyiVersion"

# ---------- 3. Prerequisite: Inno Setup (ISCC.exe) ----------
Write-Step "Checking for Inno Setup (ISCC.exe)"
$IsccCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
)
$Iscc = $null
foreach ($candidate in $IsccCandidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) { $Iscc = $candidate; break }
}
if (-not $Iscc) {
    Fail "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php (default 'Inno Setup 6' location) and re-run this script. Looked in:`n    $($IsccCandidates -join "`n    ")"
}
Write-Host "    ISCC: $Iscc"

# ---------- 4. Clean previous build / dist output ----------
Write-Step "Cleaning previous build output"
foreach ($path in @($WorkPath, $DistPath)) {
    if (Test-Path -LiteralPath $path) {
        Write-Host "    Removing $path"
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}
if (Test-Path -LiteralPath $InstallerExe) {
    Write-Host "    Removing $InstallerExe"
    Remove-Item -LiteralPath $InstallerExe -Force
}

# ---------- 5. Build the onedir bundle ----------
Write-Step "Running PyInstaller (onedir, UPX disabled)"
& $Python -m PyInstaller --noconfirm --clean --distpath $DistPath --workpath $WorkPath $SpecPath
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller failed (exit code $LASTEXITCODE)." }

$BuiltExe = Join-Path $BundleDir 'JustDownloadIT.exe'
if (-not (Test-Path -LiteralPath $BuiltExe)) {
    Fail "PyInstaller finished but $BuiltExe was not produced."
}
Write-Host "    Built: $BuiltExe"

# ---------- 6. Compile the installer ----------
Write-Step "Compiling installer with Inno Setup"
& $Iscc $IssPath
if ($LASTEXITCODE -ne 0) { Fail "Inno Setup compilation failed (exit code $LASTEXITCODE)." }
if (-not (Test-Path -LiteralPath $InstallerExe)) {
    Fail "Inno Setup reported success but $InstallerExe was not produced."
}

# ---------- 7. Report ----------
$item  = Get-Item -LiteralPath $InstallerExe
$hash  = (Get-FileHash -LiteralPath $InstallerExe -Algorithm SHA256).Hash.ToLower()
$sizeMb = [math]::Round($item.Length / 1MB, 2)

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "  Installer : $($item.FullName)"
Write-Host "  Size      : $sizeMb MB ($($item.Length) bytes)"
Write-Host "  SHA256    : $hash"
Write-Host ""
