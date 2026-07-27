param()
Write-Host "Building LapLIS executable with PyInstaller..."
Write-Host "IMPORTANT: run this with Python 3.9 to keep the resulting .exe compatible with Windows 7."

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found. Installing..."
    pip install pyinstaller
}

# --add-data bundles the JSON reference data (test catalog/prices/ranges) and the DejaVu Sans font
# used for Arabic+Latin PDF text - the app cannot seed its database or generate PDFs without them.
pyinstaller --noconfirm --onefile --windowed --name LapLIS `
    --add-data "app/seed_data;app/seed_data" `
    --add-data "app/reports/fonts;app/reports/fonts" `
    --add-data "logo;logo" `
    main.py

Write-Host "Build complete. See dist\LapLIS.exe"
