#!/usr/bin/env bash
# Pulsar Launcher - Start WezTerm with Neovim environment
set -euo pipefail

PULSAR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PULSAR_ROOT
export PULSAR_BIN_DIR="${PULSAR_ROOT}/bin"
export PULSAR_CONFIG_DIR="${PULSAR_ROOT}/.config"
export PULSAR_CACHE_DIR="${PULSAR_ROOT}/.cache"
export PULSAR_DATA_DIR="${PULSAR_ROOT}/.local/share"
export PULSAR_STATE_DIR="${PULSAR_ROOT}/.local/state"

# Set XDG directories for portable apps
export XDG_CONFIG_HOME="${PULSAR_CONFIG_DIR}"
export XDG_CACHE_HOME="${PULSAR_CACHE_DIR}"
export XDG_DATA_HOME="${PULSAR_DATA_DIR}"
export XDG_STATE_HOME="${PULSAR_STATE_DIR}"

# UV environment variables
export UV_TOOL_DIR="${PULSAR_DATA_DIR}/uv/tools"
export UV_PYTHON_INSTALL_DIR="${PULSAR_DATA_DIR}/uv/python"
export UV_CACHE_DIR="${PULSAR_CACHE_DIR}/uv"

# Create directory structure
mkdir -p "${PULSAR_BIN_DIR}"
mkdir -p "${PULSAR_CACHE_DIR}/uv"
mkdir -p "${PULSAR_CONFIG_DIR}"
mkdir -p "${PULSAR_DATA_DIR}/uv/python"
mkdir -p "${PULSAR_DATA_DIR}/uv/tools"
mkdir -p "${PULSAR_STATE_DIR}"

# Check if uv is already installed
if ! [[ -f "${PULSAR_BIN_DIR}/uv" ]]; then
    echo "Installing uv to ${PULSAR_BIN_DIR}..."

    # Download and install uv to the specified directory
    # Set environment variables to ensure local installation
    export UV_INSTALL_DIR="${PULSAR_BIN_DIR}"
    export INSTALLER_NO_MODIFY_PATH=1
    curl -LsSf https://astral.sh/uv/install.sh | sh

    echo ""
    echo "✓ uv installed successfully to ${PULSAR_BIN_DIR}/uv"
fi

# Add bin and UV tools to PATH
# UV installs tools to .local/bin
LOCAL_BIN_DIR="${PULSAR_ROOT}/.local/bin"
export PATH="${PULSAR_BIN_DIR}:${LOCAL_BIN_DIR}:${PATH}"

# Bootstrap: Install/reinstall CLI tool to get latest commands
PULSAR_CMD="${LOCAL_BIN_DIR}/pulsar"
if ! [[ -f "${PULSAR_CMD}" ]] || ! "${PULSAR_CMD}" --help | grep -q bootstrap; then
    echo "Installing Pulsar CLI..."
    ${PULSAR_BIN_DIR}/uv run ${PULSAR_ROOT}/install.py
fi

# Create symlink to pulsar in bin directory for easier access
if [[ -f "${PULSAR_CMD}" ]]; then
    ln -sf "../.local/bin/pulsar" "${PULSAR_BIN_DIR}/pulsar"
fi

# Install required packages (wezterm, neovim, fzf, etc.)
echo "Checking required packages..."
"${PULSAR_CMD}" bootstrap

# Launch WezTerm in current directory, detached from terminal
WEZTERM_PATH="${PULSAR_BIN_DIR}/wezterm"

if [[ ! -f "${WEZTERM_PATH}" ]] && [[ ! -L "${WEZTERM_PATH}" ]]; then
    echo "✗ WezTerm not found at ${WEZTERM_PATH}"
    echo "Checking bin directory contents:"
    ls -la "${PULSAR_BIN_DIR}/" | grep -E "wezterm|nvim|fzf"
    exit 1
fi

echo "Launching WezTerm..."
# Export PULSAR_ROOT so wezterm config can find it
PULSAR_ROOT="${PULSAR_ROOT}" nohup "${WEZTERM_PATH}" start --cwd "$(pwd)" >/dev/null 2>&1 &
disown

echo "✓ WezTerm launched in $(pwd)"
