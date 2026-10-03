
# Detect operating system
OS=$(uname -s)

if [ "$OS" != "Linux" ]; then
    echo "Error: This script only supports Linux systems" >&2
    echo "Detected OS: $OS" >&2
    exit 1
fi

# Detect platform architecture
ARCH=$(uname -m)

case "$ARCH" in
    x86_64)
        export PLATFORM="linux-x86_64"
        ;;
    aarch64|arm64)
        export PLATFORM="linux-arm_64"
        ;;
    *)
        echo "Error: Unsupported platform architecture: $ARCH" >&2
        echo "This script only supports linux-x86_64 and linux-arm_64" >&2
        exit 1
        ;;
esac

# Pulsar vars
export PULSAR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PULSAR_CONFIG_DIR="${PULSAR_ROOT}/config"
export PULSAR_SRC_DIR="${PULSAR_ROOT}/src"
export PULSAR_BIN_DIR="${PULSAR_ROOT}/bin"
export PULSAR_DATA_DIR="${PULSAR_ROOT}/data"
export PULSAR_CACHE_DIR="${PULSAR_ROOT}/.cache"
export PULSAR_STATE_DIR="${PULSAR_ROOT}/.state"
export PULSAR_VENV_DIR="${PULSAR_ROOT}/.venv"

# Create directory structure
mkdir -p "${PULSAR_BIN_DIR}"
mkdir -p "${PULSAR_DATA_DIR}"
mkdir -p "${PULSAR_CACHE_DIR}"
mkdir -p "${PULSAR_STATE_DIR}"

# Set XDG directories for portable apps
export XDG_CONFIG_HOME="${PULSAR_CONFIG_DIR}"
export XDG_CACHE_HOME="${PULSAR_CACHE_DIR}"
export XDG_DATA_HOME="${PULSAR_DATA_DIR}"
export XDG_STATE_HOME="${PULSAR_STATE_DIR}"
export PATH="${PULSAR_BIN_DIR}:${PATH}"

# UV environment variables
export UV_TOOL_DIR="${PULSAR_DATA_DIR}/uv/tools"
export UV_PYTHON_INSTALL_DIR="${PULSAR_DATA_DIR}/uv/python"
export UV_CACHE_DIR="${PULSAR_CACHE_DIR}/uv"

if [ ! -f "${PULSAR_BIN_DIR}/uv" ]; then
    echo "Extracting uv executable"
    tar -xJf "./uv/${PLATFORM}.tar.xz" -C ${PULSAR_BIN_DIR}
fi

__psr_uv_wrapper() {
    if [[ -f "${PULSAR_BIN_DIR}/uv" ]]; then
        env UV_PROJECT_ENVIRONMENT="$PULSAR_VENV_DIR" \
            VIRTUAL_ENV="$PULSAR_VENV_DIR" \
            UV_WORKING_DIR="$PULSAR_SRC_DIR" \
            "${PULSAR_BIN_DIR}/uv" "$@"
    else
        echo "uv is not installed."
    fi
}

echo "Syncing virtual environment"
__psr_uv_wrapper sync

pulsar() {
    if [[ "$1" == "uv" ]]; then
        shift
        __psr_uv_wrapper "$@"
    else
        __psr_uv_wrapper run pulsar "$@"
    fi
}

alias psr=pulsar
