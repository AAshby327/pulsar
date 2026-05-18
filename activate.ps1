# Pulsar activation script for PowerShell
# Determine PULSAR_ROOT from script location
$PULSAR_ROOT = Split-Path -Parent $PSCommandPath
$env:PULSAR_ROOT = $PULSAR_ROOT
$env:PULSAR_BIN_DIR = Join-Path $PULSAR_ROOT "bin"
$env:PULSAR_SRC_DIR = Join-Path $PULSAR_ROOT "src"
$env:PULSAR_CONFIG_DIR = Join-Path $PULSAR_ROOT "config"
$env:PULSAR_CACHE_DIR = Join-Path $PULSAR_ROOT ".cache"
$env:PULSAR_DATA_DIR = Join-Path $PULSAR_ROOT ".data"
$env:PULSAR_STATE_DIR = Join-Path $PULSAR_ROOT ".state"

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
$env:UV_PROJECT_ENVIRONMENT = "$env:PULSAR_ROOT\.venv"
$env:VIRTUAL_ENV = $env:UV_PROJECT_ENVIRONMENT

# System config for pulsar
$env:SHELL = "powershell"

# Install uv if not already installed
$uvPath = Join-Path $env:PULSAR_BIN_DIR "uv.exe"
if (-not (Test-Path $uvPath)) {
    # Download and install uv using cached installer script
    $env:UV_INSTALL_DIR = $env:PULSAR_BIN_DIR
    $env:INSTALLER_NO_MODIFY_PATH = "1"

    $cachedInstaller = Join-Path "$env:PULSAR_CACHE_DIR\uv" "install.ps1"

    try {
        $ErrorActionPreference = 'Stop'

        # Download installer script to cache if not present
        if (-not (Test-Path $cachedInstaller)) {
            $installerContent = Invoke-RestMethod https://astral.sh/uv/install.ps1
            $installerContent | Out-File -FilePath $cachedInstaller -Encoding UTF8
        }

        # Run cached installer script
        & $cachedInstaller

        & $uvPath sync --directory $env:PULSAR_SRC_DIR
    } catch {
        Write-Host "[ERROR] Failed to install uv: $_" -ForegroundColor Red
        throw
    }
}

# Add bin directory to PATH
$env:PATH = "$env:PULSAR_BIN_DIR;$env:PATH"

$output = & "$env:VIRTUAL_ENV\Scripts\python.exe" "$env:PULSAR_SRC_DIR\pulsar.py" "activate"
if ($output) {
    $outputStr = $output -join "`n"
    Invoke-Expression $outputStr
}

# Define pulsar function
function global:pulsar {
    if ($args[0] -eq "reload") {
        . "$env:PULSAR_ROOT\activate.ps1"
        return
    } else {
        & "$env:VIRTUAL_ENV\Scripts\python.exe" "$env:PULSAR_SRC_DIR\pulsar.py" $args
    }
}

# Define aliases
Set-Alias -Name psr -Value pulsar -Scope Global -Force