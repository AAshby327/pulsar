# Pulsar Launcher - Quick launch for WezTerm (PowerShell)
param()

# Determine script directory
$SCRIPT_DIR = Split-Path -Parent $PSCommandPath
$env:PULSAR_ROOT = $SCRIPT_DIR
$env:PULSAR_BIN_DIR = Join-Path $SCRIPT_DIR "bin"
$WEZTERM_EXE = Join-Path $env:PULSAR_BIN_DIR "wezterm.exe"

# Check if wezterm is installed
if (Test-Path $WEZTERM_EXE) {
    # Launch wezterm
    Start-Process -FilePath $WEZTERM_EXE
    exit 0
} else {
    # wezterm not found, offer to install
    Write-Host "================================================" -ForegroundColor Blue
    Write-Host "⭐ Pulsar Package Manager" -ForegroundColor Blue
    Write-Host "================================================" -ForegroundColor Blue
    Write-Host ""
    Write-Host "WezTerm is not installed." -ForegroundColor Yellow
    Write-Host ""

    $response = Read-Host "Would you like to install WezTerm now? [Y/n]"

    if ([string]::IsNullOrWhiteSpace($response) -or $response -match "^[Yy]") {
        Write-Host ""
        Write-Host "Installing WezTerm..." -ForegroundColor Cyan

        # Source the activation script to set up environment
        . (Join-Path $SCRIPT_DIR "activate.ps1")

        # Install wezterm using pulsar
        & "$env:PULSAR_SRC_DIR\.venv\Scripts\python.exe" "$env:PULSAR_SRC_DIR\pulsar.py" install wezterm

        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✓ Installation complete!" -ForegroundColor Green
            Write-Host "Launching WezTerm..." -ForegroundColor Cyan
            Start-Sleep -Seconds 1
            Start-Process -FilePath $WEZTERM_EXE
            exit 0
        } else {
            Write-Host ""
            Write-Host "✗ Installation failed." -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
    } else {
        Write-Host ""
        Write-Host "Installation cancelled." -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 0
    }
}
