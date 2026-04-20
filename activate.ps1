# Pulsar activation script for PowerShell
# Determine PULSAR_ROOT from script location
$PULSAR_ROOT = Split-Path -Parent $PSCommandPath
$env:PULSAR_ROOT = $PULSAR_ROOT
$env:PULSAR_BIN_DIR = Join-Path $PULSAR_ROOT "bin"
$env:PULSAR_SRC_DIR = Join-Path $PULSAR_ROOT "src"
$env:PULSAR_CONFIG_DIR = Join-Path $PULSAR_ROOT "config"
$env:PULSAR_CACHE_DIR = Join-Path $PULSAR_ROOT ".cache"
$env:PULSAR_DATA_DIR = Join-Path $PULSAR_ROOT ".local\share"
$env:PULSAR_STATE_DIR = Join-Path $PULSAR_ROOT ".local\state"

# Create directory structure
New-Item -ItemType Directory -Force -Path $env:PULSAR_BIN_DIR | Out-Null
New-Item -ItemType Directory -Force -Path "$env:PULSAR_CACHE_DIR\uv" | Out-Null
New-Item -ItemType Directory -Force -Path $env:PULSAR_CONFIG_DIR | Out-Null
New-Item -ItemType Directory -Force -Path "$env:PULSAR_DATA_DIR\uv\python" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:PULSAR_DATA_DIR\uv\tools" | Out-Null
New-Item -ItemType Directory -Force -Path $env:PULSAR_STATE_DIR | Out-Null

# Set XDG directories for portable apps
$env:XDG_CONFIG_HOME = $env:PULSAR_CONFIG_DIR
$env:XDG_CACHE_HOME = $env:PULSAR_CACHE_DIR
$env:XDG_DATA_HOME = $env:PULSAR_DATA_DIR
$env:XDG_STATE_HOME = $env:PULSAR_STATE_DIR

# UV environment variables
$env:UV_TOOL_DIR = "$env:PULSAR_DATA_DIR\uv\tools"
$env:UV_PYTHON_INSTALL_DIR = "$env:PULSAR_DATA_DIR\uv\python"
$env:UV_CACHE_DIR = "$env:PULSAR_CACHE_DIR\uv"

# TODO: Make this an optional package
# Install PowerShell if not already installed
$pwshDir = Join-Path $env:PULSAR_BIN_DIR "pwsh"
$pwshPath = Join-Path $pwshDir "pwsh.exe"
if (-not (Test-Path $pwshPath)) {
    # Get latest PowerShell release info
    $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/PowerShell/PowerShell/releases/latest"
    $asset = $releases.assets | Where-Object { $_.name -like "*win-x64.zip" -and $_.name -notlike "*arm*" } | Select-Object -First 1

    if ($asset) {
        $downloadUrl = $asset.browser_download_url
        $zipPath = Join-Path $env:PULSAR_CACHE_DIR "powershell.zip"

        # Download PowerShell
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath

        # Extract directly to final location
        New-Item -ItemType Directory -Force -Path $pwshDir | Out-Null
        Expand-Archive -Path $zipPath -DestinationPath $pwshDir -Force

        # Cleanup
        Remove-Item -Force $zipPath
    } else {
        Write-Host "[WARNING] Could not find PowerShell download, skipping installation" -ForegroundColor Yellow
    }
}

# Add PowerShell to PATH if installed
if (Test-Path $pwshPath) {
    $env:PATH = "$pwshDir;$env:PATH"
}

# Install uv if not already installed
$uvPath = Join-Path $env:PULSAR_BIN_DIR "uv.exe"
if (-not (Test-Path $uvPath)) {
    # Download and install uv
    $env:UV_INSTALL_DIR = $env:PULSAR_BIN_DIR
    $env:INSTALLER_NO_MODIFY_PATH = "1"

    try {
        $ErrorActionPreference = 'Stop'
        irm https://astral.sh/uv/install.ps1 | iex *>&1 | Out-Null
    } catch {
        Write-Host "[ERROR] Failed to install uv: $_" -ForegroundColor Red
        throw
    }
}

# Install pulsar system packages
& $uvPath sync --directory $env:PULSAR_SRC_DIR --quiet

# Add bin directory to PATH
$env:PATH = "$env:PULSAR_BIN_DIR;$env:PATH"

# Define pulsar function
function pulsar {
    param(
        [Parameter(ValueFromRemainingArguments=$true)]
        $Args
    )

    if ($Args.Count -gt 0 -and $Args[0] -eq "activate") {
        # For activate command, capture and execute the output
        $output = & "$env:PULSAR_SRC_DIR\.venv\Scripts\python.exe" "$env:PULSAR_SRC_DIR\pulsar.py" @Args
        Invoke-Expression $output
    } else {
        # Pass through other commands normally
        & "$env:PULSAR_SRC_DIR\.venv\Scripts\python.exe" "$env:PULSAR_SRC_DIR\pulsar.py" @Args
    }
}

# Define alias
Set-Alias -Name psr -Value pulsar

# Launch local PowerShell session if installed (only if not already in a Pulsar pwsh session)
if (-not $env:PULSAR_PWSH_LAUNCHED) {
    $pwshDir = Join-Path $env:PULSAR_BIN_DIR "pwsh"
    $pwshPath = Join-Path $pwshDir "pwsh.exe"
    if (Test-Path $pwshPath) {
        # Set flag to prevent recursive launches
        $env:PULSAR_PWSH_LAUNCHED = "1"
        # Launch new session and re-source this script to get functions/aliases
        & $pwshPath -NoLogo -NoExit -Command ". '$PSCommandPath'"
    } else {
        Write-Host "[WARNING] Local PowerShell not found, staying in current session" -ForegroundColor Yellow
    }
}