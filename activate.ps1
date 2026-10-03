# Detect operating system
if (-not $IsWindows -and $PSVersionTable.PSVersion.Major -ge 6) {
    Write-Error "Error: This script only supports Windows systems"
    Write-Error "Detected OS: $($PSVersionTable.OS)"
    exit 1
}

# Detect platform architecture
$Arch = [System.Environment]::GetEnvironmentVariable('PROCESSOR_ARCHITECTURE')

if ($Arch -ne 'AMD64') {
    Write-Error "Error: Unsupported platform architecture: $Arch"
    Write-Error "This script only supports Windows x86_64 (AMD64)"
    exit 1
}

$env:PLATFORM = "win-x86_64"

# Pulsar vars
$env:PULSAR_ROOT = $PSScriptRoot
$env:PULSAR_CONFIG_DIR = Join-Path $env:PULSAR_ROOT "config"
$env:PULSAR_SRC_DIR = Join-Path $env:PULSAR_ROOT "src"
$env:PULSAR_BIN_DIR = Join-Path $env:PULSAR_ROOT "bin"
$env:PULSAR_DATA_DIR = Join-Path $env:PULSAR_ROOT "data"
$env:PULSAR_CACHE_DIR = Join-Path $env:PULSAR_ROOT ".cache"
$env:PULSAR_STATE_DIR = Join-Path $env:PULSAR_ROOT ".state"
$env:PULSAR_VENV_DIR = Join-Path $env:PULSAR_ROOT ".venv"

# Create directory structure
New-Item -ItemType Directory -Force -Path $env:PULSAR_BIN_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:PULSAR_DATA_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:PULSAR_CACHE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:PULSAR_STATE_DIR | Out-Null

# Set XDG directories for portable apps
$env:XDG_CONFIG_HOME = $env:PULSAR_CONFIG_DIR
$env:XDG_CACHE_HOME = $env:PULSAR_CACHE_DIR
$env:XDG_DATA_HOME = $env:PULSAR_DATA_DIR
$env:XDG_STATE_HOME = $env:PULSAR_STATE_DIR
$env:PATH = "$env:PULSAR_BIN_DIR;$env:PATH"

# UV environment variables
$env:UV_TOOL_DIR = Join-Path $env:PULSAR_DATA_DIR "uv\tools"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $env:PULSAR_DATA_DIR "uv\python"
$env:UV_CACHE_DIR = Join-Path $env:PULSAR_CACHE_DIR "uv"

$UV_EXE_PATH = Join-Path $env:PULSAR_BIN_DIR "uv.exe"

if (-not (Test-Path $UV_EXE_PATH)) {
    Write-Host "Extracting uv executable"
    $uvZipPath = Join-Path $env:PULSAR_ROOT "uv\$env:PLATFORM.zip"

    # Extract using built-in PowerShell (available in PowerShell 5.0+)
    Expand-Archive -Path $uvZipPath -DestinationPath $env:PULSAR_BIN_DIR -Force
}

# UV wrapper function
function __psr_uv_wrapper {
    if (Test-Path $UV_EXE_PATH) {
        $env:UV_PROJECT_ENVIRONMENT = $env:PULSAR_VENV_DIR
        $env:VIRTUAL_ENV = $env:PULSAR_VENV_DIR
        $env:UV_WORKING_DIR = $env:PULSAR_SRC_DIR
        & $UV_EXE_PATH @args
    } else {
        Write-Error "uv is not installed."
    }
}

Write-Host "Syncing virtual environment"
__psr_uv_wrapper sync

# Pulsar function
function pulsar {
    if ($args.Count -gt 0 -and $args[0] -eq "uv") {
        if ($args.Count -gt 1) {
            $remainingArgs = $args[1..($args.Count-1)]
            __psr_uv_wrapper @remainingArgs
        } else {
            __psr_uv_wrapper
        }
    } else {
        __psr_uv_wrapper run pulsar @args
    }
}

# Alias
Set-Alias -Name psr -Value pulsar

