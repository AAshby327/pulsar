PULSAR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PULSAR_ROOT
export PULSAR_BIN_DIR="${PULSAR_ROOT}/bin"
export PULSAR_SRC_DIR="${PULSAR_ROOT}/src"
export PULSAR_CONFIG_DIR="${PULSAR_ROOT}/config"
export PULSAR_CACHE_DIR="${PULSAR_ROOT}/.cache"
export PULSAR_DATA_DIR="${PULSAR_ROOT}/.data"
export PULSAR_STATE_DIR="${PULSAR_ROOT}/.state"
export PULSAR_VENV_DIR="${PULSAR_ROOT}/.venv"

# Create directory structure
mkdir -p "${PULSAR_BIN_DIR}"
mkdir -p "${PULSAR_CACHE_DIR}/uv"
mkdir -p "${PULSAR_CONFIG_DIR}"
mkdir -p "${PULSAR_DATA_DIR}/uv/python"
mkdir -p "${PULSAR_DATA_DIR}/uv/tools"
mkdir -p "${PULSAR_STATE_DIR}"

# Set XDG directories for portable apps
export XDG_CONFIG_HOME="${PULSAR_CONFIG_DIR}"
export XDG_CACHE_HOME="${PULSAR_CACHE_DIR}"
export XDG_DATA_HOME="${PULSAR_DATA_DIR}"
export XDG_STATE_HOME="${PULSAR_STATE_DIR}"

# UV environment variables
export UV_TOOL_DIR="${PULSAR_DATA_DIR}/uv/tools"
export UV_PYTHON_INSTALL_DIR="${PULSAR_DATA_DIR}/uv/python"
export UV_CACHE_DIR="${PULSAR_CACHE_DIR}/uv"

# System config for pulsar
export SHELL="bash"
export OUTPUT_DELIMITER="###SHELL###"

PULSAR_UV_WRAPPER() {
    local prev_uv_project_environment=${UV_PROJECT_ENVIRONMENT:-}
    local prev_virtual_env=${VIRTUAL_ENV:-}
    local prev_uv_working_dir=${UV_WORKING_DIR:-}

    export UV_PROJECT_ENVIRONMENT=$PULSAR_VENV_DIR
    export VIRTUAL_ENV=$PULSAR_VENV_DIR
    export UV_WORKING_DIR=$PULSAR_SRC_DIR

    if [[ -f "${PULSAR_BIN_DIR}/uv" ]]; then
        ${PULSAR_BIN_DIR}/uv "$@"
    else
        echo "UV is not installed."
    fi

    # Restore or unset environment variables
    if [[ -n $prev_uv_project_environment ]]; then
        export UV_PROJECT_ENVIRONMENT=$prev_uv_project_environment
    else
        unset UV_PROJECT_ENVIRONMENT
    fi

    if [[ -n $prev_virtual_env ]]; then
        export VIRTUAL_ENV=$prev_virtual_env
    else
        unset VIRTUAL_ENV
    fi

    if [[ -n $prev_uv_working_dir ]]; then
        export UV_WORKING_DIR=$prev_uv_working_dir
    else
        unset UV_WORKING_DIR
    fi
}

# Install uv if not already
if ! [[ -f "${PULSAR_BIN_DIR}/uv" ]]; then
    # Download and install uv using cached installer script
    export UV_INSTALL_DIR="${PULSAR_BIN_DIR}"
    export INSTALLER_NO_MODIFY_PATH=1

    CACHED_INSTALLER="${PULSAR_CACHE_DIR}/uv/install.sh"

    # Download installer script to cache if not present
    if [[ ! -f "${CACHED_INSTALLER}" ]]; then
        curl -LsSf https://astral.sh/uv/install.sh -o "${CACHED_INSTALLER}"
    fi

    # Run cached installer script
    sh "${CACHED_INSTALLER}"

    PULSAR_UV_WRAPPER sync
fi

# Add bin and UV tools to PATH
export PATH="${PULSAR_BIN_DIR}:${PATH}"

eval "$(${PULSAR_VENV_DIR}/bin/python ${PULSAR_SRC_DIR}/pulsar.py activate)"

pulsar() {
    PULSAR_UV_WRAPPER run ${PULSAR_SRC_DIR}/pulsar.py "$@"
}

alias psr=pulsar