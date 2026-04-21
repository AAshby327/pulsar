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

$output = & "$env:PULSAR_SRC_DIR\.venv\Scripts\python.exe" "$env:PULSAR_SRC_DIR\pulsar.py" "activate" "--shell" "powershell"
Invoke-Expression $output

# Define pulsar function
function pulsar {
    param(
        [Parameter(ValueFromRemainingArguments=$true)]
        $Args
    )

    if ($Args[0] -eq "reload") {
        & "$env:PULSAR_ROOT\activate.ps1"
    } elseif ($Args[0] -eq "reset") {
        Write-Host "⚠️  This will delete .cache, .local, bin, and src\.venv in $env:PULSAR_ROOT"
        $confirm = Read-Host "Are you sure? (yes/no)"
        if ($confirm -eq "yes") {
            Write-Host "🔄 Resetting Pulsar environment..."
            Set-Location $env:PULSAR_ROOT
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .cache, .local, bin, src\.venv
            Write-Host "✓ Directories deleted, re-activating..."
            & "$env:PULSAR_ROOT\activate.ps1"
        } else {
            Write-Host "Reset cancelled"
        }
    } else {
        & "$env:PULSAR_SRC_DIR\.venv\Scripts\python.exe" "$env:PULSAR_SRC_DIR\pulsar.py" @Args
    }
}

# Define alias
Set-Alias -Name psr -Value pulsar