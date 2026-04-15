param(
    [string]$CondaEnv = "ies",
    [string]$AppName = "ImageEXIFStyler",
    [string]$InstallDir = "",
    [switch]$InstallPyInstaller,
    [switch]$Clean,
    [switch]$Console,
    [switch]$IncludeHeif,
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$BuildIconPath = Join-Path ([System.IO.Path]::GetTempPath()) "$AppName-brand-logo.ico"
$OneFileExePath = Join-Path $DistRoot "$AppName.exe"
$OneDirAppPath = Join-Path $DistRoot $AppName
$PackageRoot = if ($OneFile) { $DistRoot } else { $OneDirAppPath }
$ExePath = Join-Path $PackageRoot "$AppName.exe"
$ResourceDirectories = @(
    "config",
    "UI\template_images"
)
$ResourceFiles = @(
    "LICENSE",
    "README.md",
    "UI\logo.avg",
    "UI\logo.svg",
    "UI\logo.ico",
    "UI\logo.png",
    "UI\logo.jpg",
    "UI\logo.jpeg"
)
$RuntimeDirectories = @(
    "input",
    "output",
    "logs"
)

Set-Location $ProjectRoot
$env:PYTHONDONTWRITEBYTECODE = "1"

function Invoke-CondaPython {
    param([string[]]$Arguments)

    & conda run -n $CondaEnv python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "conda run -n $CondaEnv python $($Arguments -join ' ') failed."
    }
}

function Copy-DirectoryClean {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Required directory was not found: $Source"
    }

    if (Test-Path -LiteralPath $Destination) {
        Remove-PathWithRetry -Path $Destination -Recurse
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Copy-FileOverwrite {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Required file was not found: $Source"
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Resolve-TargetPath {
    param([string]$Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path))
}

function Get-ExistingProjectFile {
    param([string[]]$RelativePaths)

    foreach ($relativePath in $RelativePaths) {
        $candidate = Join-Path $ProjectRoot $relativePath
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Remove-PathWithRetry {
    param(
        [string]$Path,
        [switch]$Recurse
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            if ($Recurse) {
                Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            } else {
                Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
            }
            return
        } catch {
            if ($attempt -eq 5) {
                throw "Could not remove '$Path'. Close any running $AppName.exe process and retry. $($_.Exception.Message)"
            }
            Start-Sleep -Seconds 1
        }
    }
}

function Copy-RuntimeResources {
    param([string]$TargetDir)

    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

    foreach ($dirName in $ResourceDirectories) {
        Copy-DirectoryClean -Source (Join-Path $ProjectRoot $dirName) -Destination (Join-Path $TargetDir $dirName)
    }

    foreach ($dirName in $RuntimeDirectories) {
        New-Item -ItemType Directory -Path (Join-Path $TargetDir $dirName) -Force | Out-Null
    }

    foreach ($fileName in $ResourceFiles) {
        $sourceFile = Join-Path $ProjectRoot $fileName
        if (Test-Path -LiteralPath $sourceFile) {
            Copy-FileOverwrite -Source $sourceFile -Destination (Join-Path $TargetDir $fileName)
        }
    }
}

function Copy-PackageFiles {
    param([string]$TargetDir)

    if ($OneFile) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
        $targetExe = Join-Path $TargetDir "$AppName.exe"
        if ([System.IO.Path]::GetFullPath($ExePath) -ne [System.IO.Path]::GetFullPath($targetExe)) {
            Copy-FileOverwrite -Source $ExePath -Destination $targetExe
        }
        Copy-RuntimeResources -TargetDir $TargetDir
        return
    }

    if ([System.IO.Path]::GetFullPath($PackageRoot) -eq [System.IO.Path]::GetFullPath($TargetDir)) {
        return
    }

    Copy-DirectoryClean -Source $PackageRoot -Destination $TargetDir
}

function New-IconFromLogo {
    param(
        [string]$Source,
        [string]$Destination
    )

    $iconScript = @'
import base64
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
destination.parent.mkdir(parents=True, exist_ok=True)

if source.suffix.lower() == ".ico":
    destination.write_bytes(source.read_bytes())
    raise SystemExit(0)

if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}:
    image = Image.open(source)
else:
    content = source.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"data:image/(?:png|jpg|jpeg);base64,([^\"']+)", content, re.IGNORECASE | re.DOTALL)
    if not match:
        raise SystemExit(f"Could not find an embedded PNG/JPEG logo in {source}. Provide UI/logo.ico to set the exe icon.")
    image_data = base64.b64decode(re.sub(r"\s+", "", match.group(1)))
    image = Image.open(BytesIO(image_data))

image.convert("RGBA").save(
    destination,
    format="ICO",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
'@

    $iconScriptPath = Join-Path ([System.IO.Path]::GetTempPath()) "$AppName-icon-builder.py"
    try {
        Set-Content -LiteralPath $iconScriptPath -Value $iconScript -Encoding UTF8
        Invoke-CondaPython @($iconScriptPath, $Source, $Destination)
    } finally {
        if (Test-Path -LiteralPath $iconScriptPath) {
            Remove-Item -LiteralPath $iconScriptPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Resolve-PyInstallerIcon {
    $existingIcon = Get-ExistingProjectFile @("UI\logo.ico")
    if ($existingIcon) {
        return $existingIcon
    }

    $logoSource = Get-ExistingProjectFile @(
        "UI\logo.avg",
        "UI\logo.svg",
        "UI\logo.png",
        "UI\logo.jpg",
        "UI\logo.jpeg"
    )
    if (-not $logoSource) {
        Write-Warning "No UI logo file was found. The packaged exe will use the default executable icon."
        return $null
    }

    New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
    New-IconFromLogo -Source $logoSource -Destination $BuildIconPath
    Write-Host "Using application icon: $BuildIconPath"
    return $BuildIconPath
}

function Resolve-QtBinding {
    $binding = & conda run -n $CondaEnv python -c "import importlib.util as u; print('PySide6' if u.find_spec('PySide6') else 'PyQt5' if u.find_spec('PyQt5') else '')"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not detect Qt binding in conda env '$CondaEnv'."
    }

    $binding = ($binding | Select-Object -First 1).Trim()
    if (-not $binding) {
        throw "Neither PySide6 nor PyQt5 is installed in conda env '$CondaEnv'."
    }

    return $binding
}

& conda run -n $CondaEnv python --version
if ($LASTEXITCODE -ne 0) {
    throw "Conda environment '$CondaEnv' is not available. Create it first or pass -CondaEnv <name>."
}

$pyInstallerVersion = & conda run -n $CondaEnv python -c "import PyInstaller; print(PyInstaller.__version__)" 2>$null
if ($LASTEXITCODE -ne 0) {
    if (-not $InstallPyInstaller) {
        throw "PyInstaller is not installed in conda env '$CondaEnv'. Re-run with -InstallPyInstaller."
    }

    Invoke-CondaPython @("-m", "pip", "install", "pyinstaller")
    $pyInstallerVersion = & conda run -n $CondaEnv python -c "import PyInstaller; print(PyInstaller.__version__)"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller installation did not complete successfully."
    }
}
Write-Host "PyInstaller: $pyInstallerVersion"

if ($Clean) {
    if (Test-Path -LiteralPath $BuildRoot) {
        Remove-PathWithRetry -Path $BuildRoot -Recurse
    }
    Remove-PathWithRetry -Path (Join-Path $DistRoot "installer") -Recurse
}

Remove-PathWithRetry -Path $OneFileExePath
Remove-PathWithRetry -Path $OneDirAppPath -Recurse

$windowMode = if ($Console) { "--console" } else { "--windowed" }
$bundleMode = if ($OneFile) { "--onefile" } else { "--onedir" }
Write-Host "Bundle mode: $(if ($OneFile) { 'onefile' } else { 'onedir with DLL dependencies' })"
$iconPath = Resolve-PyInstallerIcon
$qtBinding = Resolve-QtBinding
Write-Host "Qt binding: $qtBinding"

$excludedModules = @(
    "numpy",
    "cv2",
    "matplotlib",
    "scipy",
    "loguru",
    "IPython",
    "ipykernel"
)
if ($qtBinding -eq "PySide6") {
    $excludedModules += "PyQt5"
} else {
    $excludedModules += "PySide6"
}

$pyinstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm",
    $bundleMode,
    $windowMode,
    "--name", $AppName,
    "--distpath", $DistRoot,
    "--workpath", $BuildRoot,
    "--specpath", $BuildRoot,
    "--hidden-import", "processor.filters",
    "--hidden-import", "processor.generators",
    "--hidden-import", "processor.mergers"
)
if ($iconPath) {
    $pyinstallerArgs += @("--icon", $iconPath)
}
if ($IncludeHeif) {
    $pyinstallerArgs += @("--collect-all", "pillow_heif")
    Write-Host "HEIC support: included"
} else {
    $excludedModules += "pillow_heif"
    Write-Host "HEIC support: excluded (pass -IncludeHeif to enable)"
}
foreach ($moduleName in $excludedModules) {
    $pyinstallerArgs += @("--exclude-module", $moduleName)
}
$pyinstallerArgs += "main.py"

if ($Clean) {
    $pyinstallerArgs = @("-m", "PyInstaller", "--clean") + $pyinstallerArgs[2..($pyinstallerArgs.Count - 1)]
}

Invoke-CondaPython $pyinstallerArgs

Copy-RuntimeResources -TargetDir $PackageRoot

if ($InstallDir.Trim()) {
    $targetDir = Resolve-TargetPath $InstallDir
    Copy-PackageFiles -TargetDir $targetDir
    Write-Host "Installed $AppName to: $targetDir"
}

Write-Host "Package ready: $PackageRoot"
Write-Host "Executable: $ExePath"
