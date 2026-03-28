#!/usr/bin/env pwsh
# Pulsar Launcher - Start WezTerm with Neovim environment (Windows)
$ErrorActionPreference = "Stop"

# Set Pulsar root directory
$PULSAR_ROOT = $PSScriptRoot
$env:PULSAR_ROOT = $PULSAR_ROOT
$env:PULSAR_BIN_DIR = Join-Path $PULSAR_ROOT "bin"
$env:PULSAR_CONFIG_DIR = Join-Path $PULSAR_ROOT ".config"
$env:PULSAR_CACHE_DIR = Join-Path $PULSAR_ROOT ".cache"
$env:PULSAR_DATA_DIR = Join-Path $PULSAR_ROOT ".local\share"
$env:PULSAR_STATE_DIR = Join-Path $PULSAR_ROOT ".local\state"

# Set XDG directories for portable apps
$env:XDG_CONFIG_HOME = $env:PULSAR_CONFIG_DIR
$env:XDG_CACHE_HOME = $env:PULSAR_CACHE_DIR
$env:XDG_DATA_HOME = $env:PULSAR_DATA_DIR
$env:XDG_STATE_HOME = $env:PULSAR_STATE_DIR

# UV environment variables
$env:UV_TOOL_DIR = Join-Path $env:PULSAR_DATA_DIR "uv\tools"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $env:PULSAR_DATA_DIR "uv\python"
$env:UV_CACHE_DIR = Join-Path $env:PULSAR_CACHE_DIR "uv"

# Create directory structure
$directories = @(
    $env:PULSAR_BIN_DIR,
    (Join-Path $env:PULSAR_CACHE_DIR "uv"),
    $env:PULSAR_CONFIG_DIR,
    (Join-Path $env:PULSAR_DATA_DIR "uv\python"),
    (Join-Path $env:PULSAR_DATA_DIR "uv\tools"),
    $env:PULSAR_STATE_DIR
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Check if uv is already installed
$uvPath = Join-Path $env:PULSAR_BIN_DIR "uv.exe"
if (-not (Test-Path $uvPath)) {
    Write-Host "Installing uv to $env:PULSAR_BIN_DIR..."

    # Download and install uv
    $env:UV_INSTALL_DIR = $env:PULSAR_BIN_DIR
    $env:INSTALLER_NO_MODIFY_PATH = "1"

    # Download and run installer
    Invoke-Expression "& { $(Invoke-RestMethod https://astral.sh/uv/install.ps1) }"

    Write-Host ""
    Write-Host "✓ uv installed successfully to $uvPath"
}

# Add bin and UV tools to PATH
# On Windows, UV installs tools to .local\bin
$localBinDir = Join-Path (Split-Path $env:PULSAR_DATA_DIR -Parent) "bin"
$env:PATH = "$env:PULSAR_BIN_DIR;$localBinDir;$env:PATH"

# Bootstrap: Install/reinstall CLI tool to get latest commands
$pulsarCmd = Get-Command pulsar -ErrorAction SilentlyContinue
$needsInstall = $false

if ($null -eq $pulsarCmd) {
    $needsInstall = $true
} else {
    # Check if bootstrap command exists
    $helpOutput = & pulsar --help 2>&1 | Out-String
    if ($helpOutput -notmatch "bootstrap") {
        $needsInstall = $true
    }
}

if ($needsInstall) {
    Write-Host "Installing Pulsar CLI..."
    & $uvPath run (Join-Path $PULSAR_ROOT "install.py")

    # Refresh the pulsar command reference after installation
    $pulsarCmd = Get-Command pulsar -ErrorAction SilentlyContinue
}

# Create symlink to pulsar in bin directory for easier access
$pulsarPath = Join-Path $localBinDir "pulsar.exe"
$pulsarBinLink = Join-Path $env:PULSAR_BIN_DIR "pulsar.exe"
if ((Test-Path $pulsarPath) -and -not (Test-Path $pulsarBinLink)) {
    # On Windows, copy instead of symlink for better compatibility
    Copy-Item $pulsarPath $pulsarBinLink -Force
}

# Install required packages (wezterm, neovim, fzf, etc.)
Write-Host "Checking required packages..."

# Use full path to pulsar to ensure it's found
$pulsarPath = Join-Path $localBinDir "pulsar.exe"

if (Test-Path $pulsarPath) {
    & $pulsarPath bootstrap
} else {
    Write-Error "pulsar executable not found at $pulsarPath"
    exit 1
}

# Get current directory for wezterm
$currentDir = Get-Location

# Launch WezTerm in current directory, detached from terminal
$weztermPath = Join-Path $env:PULSAR_BIN_DIR "wezterm.exe"
if (Test-Path $weztermPath) {
    # Start wezterm detached
    # Use full path for --cwd and quote it
    $cwdArg = "--cwd=`"$currentDir`""
    Start-Process -FilePath $weztermPath -ArgumentList "start", $cwdArg -WindowStyle Normal

    # Exit immediately so the PowerShell window closes
    # This prevents the PowerShell window from staying open and closing wezterm when it closes
    exit 0
} else {
    Write-Error "WezTerm not found at $weztermPath. Bootstrap may have failed."
    exit 1
}
