param(
    [string]$Arch = "x86"
)
Write-Host "Building LapLIS executable with PyInstaller..."
Write-Host "IMPORTANT: run this with Python 3.9 to keep the resulting .exe compatible with Windows 7."
Write-Host "Target architecture: $Arch"

# Always use the laplis conda environment which has PySide2 installed.
# Using any other Python/PyInstaller will produce an exe that crashes with
# "No compatible Qt binding found" because PySide2 won't be bundled.
# Dynamically resolve pyinstaller in laplis conda environment or system PATH
$LAPLIS_PYINSTALLER = Join-Path $env:USERPROFILE "miniconda3\envs\laplis\Scripts\pyinstaller.exe"

if (-not (Test-Path $LAPLIS_PYINSTALLER)) {
    $cmd = Get-Command pyinstaller -ErrorAction SilentlyContinue
    if ($cmd) {
        $LAPLIS_PYINSTALLER = $cmd.Path
    } else {
        Write-Error "laplis conda environment not found. Please activate your laplis environment and ensure pyinstaller is installed."
        exit 1
    }
}

$pythonArch = & python -c "import struct; print(struct.calcsize('P') * 8)"
if ($Arch -eq 'x86' -and $pythonArch -ne 32) {
    Write-Warning "Requested x86 build but Python interpreter is $pythonArch-bit. Use a 32-bit Python 3.9 environment for Windows 7 x86 builds."
}
if ($Arch -eq 'amd64' -and $pythonArch -ne 64) {
    Write-Warning "Requested amd64 build but Python interpreter is $pythonArch-bit. Use a 64-bit Python environment for amd64 builds."
}

# Expose architecture to the spec file
$env:LAPLIS_ARCH = $Arch

# Kill any running instance so PyInstaller can overwrite the exe
taskkill /F /IM "mostafa elznaty.exe" /T 2>$null

# Ensure build directory exists (Windows can't create paths with spaces automatically)
New-Item -ItemType Directory -Force -Path "build\mostafa elznaty" | Out-Null

# Build using the laplis conda pyinstaller
# --add-data bundles the JSON reference data (test catalog/prices/ranges) and the DejaVu Sans font
# used for Arabic+Latin PDF text - the app cannot seed its database or generate PDFs without them.
& $LAPLIS_PYINSTALLER --noconfirm --clean "mostafa elznaty.spec"

Write-Host "Build complete. See dist\mostafa elznaty.exe"
