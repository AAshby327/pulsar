# Pulsar activation script for PowerShell
# Determine PULSAR_ROOT from script location or use existing value
if (-not $env:PULSAR_ROOT) {
    $PULSAR_ROOT = Split-Path -Parent $PSCommandPath
    $env:PULSAR_ROOT = $PULSAR_ROOT
} else {
    $PULSAR_ROOT = $env:PULSAR_ROOT
}
$env:PULSAR_BIN_DIR = Join-Path $PULSAR_ROOT "bin"
$env:PULSAR_SRC_DIR = Join-Path $PULSAR_ROOT "src"
$env:PULSAR_CONFIG_DIR = Join-Path $PULSAR_ROOT "config"
$env:PULSAR_CACHE_DIR = Join-Path $PULSAR_ROOT ".cache"
$env:PULSAR_DATA_DIR = Join-Path $PULSAR_ROOT ".data"
$env:PULSAR_STATE_DIR = Join-Path $PULSAR_ROOT ".state"
$env:PULSAR_VENV_DIR = Join-Path $PULSAR_ROOT ".venv"

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

# System config for pulsar
$env:SHELL = "powershell"
$env:OUTPUT_DELIMITER = "###SHELL###"

# UV wrapper function that temporarily sets environment variables
function PULSAR_UV_WRAPPER {
    # Save current environment variables
    $prevUvProjectEnv = $env:UV_PROJECT_ENVIRONMENT
    $prevVirtualEnv = $env:VIRTUAL_ENV
    $prevUvWorkingDir = $env:UV_WORKING_DIR

    # Set temporary environment variables
    $env:UV_PROJECT_ENVIRONMENT = $env:PULSAR_VENV_DIR
    $env:VIRTUAL_ENV = $env:PULSAR_VENV_DIR
    $env:UV_WORKING_DIR = $env:PULSAR_SRC_DIR

    try {
        $uvPath = Join-Path $env:PULSAR_BIN_DIR "uv.exe"
        if (Test-Path $uvPath) {
            & $uvPath @args
        } else {
            Write-Host "UV is not installed."
        }
    } finally {
        # Restore or unset environment variables
        if ($null -ne $prevUvProjectEnv) {
            $env:UV_PROJECT_ENVIRONMENT = $prevUvProjectEnv
        } else {
            Remove-Item Env:\UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue
        }

        if ($null -ne $prevVirtualEnv) {
            $env:VIRTUAL_ENV = $prevVirtualEnv
        } else {
            Remove-Item Env:\VIRTUAL_ENV -ErrorAction SilentlyContinue
        }

        if ($null -ne $prevUvWorkingDir) {
            $env:UV_WORKING_DIR = $prevUvWorkingDir
        } else {
            Remove-Item Env:\UV_WORKING_DIR -ErrorAction SilentlyContinue
        }
    }
}

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

        PULSAR_UV_WRAPPER sync
    } catch {
        Write-Host "[ERROR] Failed to install uv: $_" -ForegroundColor Red
        throw
    }
}

# Add bin directory to PATH
$env:PATH = "$env:PULSAR_BIN_DIR;$env:PATH"

$output = & "$env:PULSAR_VENV_DIR\Scripts\python.exe" "$env:PULSAR_SRC_DIR\pulsar.py" "activate"
if ($output) {
    $outputStr = $output -join "`n"
    Invoke-Expression $outputStr
}

# Define pulsar function
function global:pulsar {
    PULSAR_UV_WRAPPER run "$env:PULSAR_SRC_DIR\pulsar.py" @args
}

# Define aliases
Set-Alias -Name psr -Value pulsar -Scope Global -Force