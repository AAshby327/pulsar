#!/usr/bin/env bash
# Pulsar Environment Activation
# Source this file to activate the environment: source ./activate.sh

PULSAR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PULSAR_ROOT
export PULSAR_BIN_DIR="${PULSAR_ROOT}/bin"
export PULSAR_CONFIG_DIR="${PULSAR_ROOT}/.config"
export PULSAR_CACHE_DIR="${PULSAR_ROOT}/.cache"
export PULSAR_DATA_DIR="${PULSAR_ROOT}/.local/share"
export PULSAR_STATE_DIR="${PULSAR_ROOT}/.local/state"

export XDG_CONFIG_HOME="${PULSAR_CONFIG_DIR}"
export XDG_CACHE_HOME="${PULSAR_CACHE_DIR}"
export XDG_DATA_HOME="${PULSAR_DATA_DIR}"
export XDG_STATE_HOME="${PULSAR_STATE_DIR}"

export UV_TOOL_DIR="${PULSAR_DATA_DIR}/uv/tools"
export UV_PYTHON_INSTALL_DIR="${PULSAR_DATA_DIR}/uv/python"
export UV_CACHE_DIR="${PULSAR_CACHE_DIR}/uv"

# Add bin and UV tools to PATH
export PATH="${PULSAR_BIN_DIR}:${UV_TOOL_DIR}/pulsar-cli/bin:${PATH}"

echo "Pulsar environment activated!"
echo "  WezTerm: ${PULSAR_BIN_DIR}/wezterm"
echo "  Neovim:  ${PULSAR_BIN_DIR}/nvim"
echo "  Run './launch.sh' to start WezTerm with Neovim"
