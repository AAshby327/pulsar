# Pulsar PowerShell initialization script

# Set PULSAR_ROOT to the directory containing this script
$env:PULSAR_ROOT = $PSScriptRoot
$env:PULSAR_BIN_DIR = Join-Path $env:PULSAR_ROOT "bin"
$env:PULSAR_SRC_DIR = Join-Path $env:PULSAR_ROOT "src"
$env:PULSAR_CONFIG_DIR = Join-Path $env:PULSAR_ROOT "config"
$env:PULSAR_CACHE_DIR = Join-Path $env:PULSAR_ROOT ".cache"
$env:PULSAR_DATA_DIR = Join-Path $env:PULSAR_ROOT ".local\share"
$env:PULSAR_STATE_DIR = Join-Path $env:PULSAR_ROOT ".local\state"

# Create directory structure
New-Item -ItemType Directory -Force -Path $env:PULSAR_BIN_DIR | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:PULSAR_CACHE_DIR "uv") | Out-Null
New-Item -ItemType Directory -Force -Path $env:PULSAR_CONFIG_DIR | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:PULSAR_DATA_DIR "uv\python") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $env:PULSAR_DATA_DIR "uv\tools") | Out-Null
New-Item -ItemType Directory -Force -Path $env:PULSAR_STATE_DIR | Out-Null

# Set XDG directories for portable apps
$env:XDG_CONFIG_HOME = $env:PULSAR_CONFIG_DIR
$env:XDG_CACHE_HOME = $env:PULSAR_CACHE_DIR
$env:XDG_DATA_HOME = $env:PULSAR_DATA_DIR
$env:XDG_STATE_HOME = $env:PULSAR_STATE_DIR

# UV environment variables
$env:UV_TOOL_DIR = Join-Path $env:PULSAR_DATA_DIR "uv\tools"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $env:PULSAR_DATA_DIR "uv\python"
$env:UV_CACHE_DIR = Join-Path $env:PULSAR_CACHE_DIR "uv"

# Install uv if not already present
$uvPath = Join-Path $env:PULSAR_BIN_DIR "uv.exe"
if (-not (Test-Path $uvPath)) {
    Write-Host "Installing uv to $env:PULSAR_BIN_DIR..."

    # Download and install uv to the specified directory
    $env:UV_INSTALL_DIR = $env:PULSAR_BIN_DIR
    $env:INSTALLER_NO_MODIFY_PATH = "1"

    # Download and execute the uv installer for Windows
    $installScript = Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing
    $installScriptContent = [System.Text.Encoding]::UTF8.GetString($installScript.Content)
    Invoke-Expression $installScriptContent

    # Verify installation succeeded
    if (-not (Test-Path $uvPath)) {
        Write-Error "Failed to install uv. Please install manually from https://docs.astral.sh/uv/getting-started/installation/"
        return
    }

    Write-Host ""
    Write-Host "✓ uv installed successfully to $uvPath"
}

# Install pulsar system packages
if (Test-Path $uvPath) {
    $pyprojectPath = Join-Path $env:PULSAR_SRC_DIR "pyproject.toml"
    if (Test-Path $pyprojectPath) {
        & $uvPath sync --directory $env:PULSAR_SRC_DIR --quiet
    } else {
        Write-Warning "pyproject.toml not found in $env:PULSAR_SRC_DIR. Skipping package sync."
        Write-Host "Run 'uv init' in the src directory to initialize a Python project."
    }
}

# Add bin directory to PATH
$env:PATH = "$env:PULSAR_BIN_DIR;$env:PATH"

# Define pulsar function
function pulsar {
    $pythonPath = Join-Path $env:PULSAR_SRC_DIR ".venv\Scripts\python.exe"
    $pulsarScript = Join-Path $env:PULSAR_SRC_DIR "pulsar.py"

    # Check if virtual environment and script exist
    if (-not (Test-Path $pythonPath)) {
        Write-Error "Python virtual environment not found at $pythonPath"
        Write-Host "Run 'uv sync --directory $env:PULSAR_SRC_DIR' to create it."
        return
    }

    if (-not (Test-Path $pulsarScript)) {
        Write-Error "pulsar.py not found at $pulsarScript"
        return
    }

    if ($args[0] -eq "activate") {
        # Capture output and execute it
        $output = & $pythonPath $pulsarScript @args
        Invoke-Expression $output
    } else {
        # Pass through other commands normally
        & $pythonPath $pulsarScript @args
    }
}

# Create alias
Set-Alias -Name psr -Value pulsar
