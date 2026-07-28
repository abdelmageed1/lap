param()
Write-Host "Building LapLIS executable with PyInstaller..."
Write-Host "IMPORTANT: run this with Python 3.9 to keep the resulting .exe compatible with Windows 7."

# Always use the laplis conda environment which has PySide2 installed.
# Using any other Python/PyInstaller will produce an exe that crashes with
# "No compatible Qt binding found" because PySide2 won't be bundled.
$LAPLIS_PYINSTALLER = "C:\Users\abdelmageed.fathy\AppData\Local\miniconda3\envs\laplis\Scripts\pyinstaller.exe"

if (-not (Test-Path $LAPLIS_PYINSTALLER)) {
    Write-Error "laplis conda environment not found at expected path. Please run: conda create -n laplis python=3.9 && pip install -r requirements.txt"
    exit 1
}

# Kill any running instance so PyInstaller can overwrite the exe
taskkill /F /IM "mostafa elznaty.exe" /T 2>$null

# Ensure build directory exists (Windows can't create paths with spaces automatically)
New-Item -ItemType Directory -Force -Path "build\mostafa elznaty" | Out-Null

# Build using the laplis conda pyinstaller
# --add-data bundles the JSON reference data (test catalog/prices/ranges) and the DejaVu Sans font
# used for Arabic+Latin PDF text - the app cannot seed its database or generate PDFs without them.
& $LAPLIS_PYINSTALLER --noconfirm --clean "mostafa elznaty.spec"

Write-Host "Build complete. See dist\mostafa elznaty.exe"
