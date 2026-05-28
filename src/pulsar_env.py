"""
Pulsar Environment Configuration

This module detects the operating system, architecture, and sets up environment
variables with sensible defaults for Pulsar package management.

All variables use environment variables if set, otherwise fall back to defaults.
"""

import os
import typing
import platform
import pathlib

# ============================================================================
# System Detection
# ============================================================================

ARCH: typing.Literal['x86_64', 'aarch64']
OS: typing.Literal['linux', 'windows']
LINUX_DISTRO: str | None
SHELL: typing.Literal['bash', 'powershell']

# Detect architecture
machine = platform.machine().lower()
if machine in ['x86_64', 'amd64', 'x64']:
    ARCH = 'x86_64'
elif machine in ['aarch64', 'arm64']:
    ARCH = 'aarch64'
else:
    raise RuntimeError(f"Unsupported architecture: {machine}")

# Detect operating system
OS = platform.system().lower()
if OS not in ['linux', 'windows']:
    raise RuntimeError(f"Unsupported operating system: {OS}")

# Detect Linux distribution
if OS == 'linux':
    try:
        os_release = platform.freedesktop_os_release()
        LINUX_DISTRO = os_release.get('ID', 'unknown')
    except (OSError, AttributeError):
        LINUX_DISTRO = 'unknown'
else:
    LINUX_DISTRO = None

# Detect shell environment
"""Detect the current shell across different operating systems."""
if not 'SHELL' in os.environ:
    raise EnvironmentError("SHELL environment variable not set.")

SHELL = os.environ['SHELL']


# ============================================================================
# Helper Functions
# ============================================================================

def _get_env_or_default(var_name: str, default_path: pathlib.Path) -> pathlib.Path:
    """Get environment variable or return default path as pathlib.Path."""
    env_value = os.environ.get(var_name)
    return pathlib.Path(env_value) if env_value else default_path


def remove_directories(*paths: pathlib.Path | str) -> None:
    for path in paths:
        print("Removing path: ", path)


# ============================================================================
# Pulsar Root Directory
# ============================================================================

# PULSAR_ROOT: Base directory for Pulsar
# Default: Current working directory
_pulsar_root_str = os.environ.get('PULSAR_ROOT') or os.getcwd()
PULSAR_ROOT = pathlib.Path(_pulsar_root_str).resolve()


# ============================================================================
# Pulsar Directories
# ============================================================================

# All Pulsar directories default to subdirectories of PULSAR_ROOT

PULSAR_BIN_DIR = _get_env_or_default(
    'PULSAR_BIN_DIR',
    PULSAR_ROOT / 'bin'
)

PULSAR_SRC_DIR = _get_env_or_default(
    'PULSAR_SRC_DIR',
    PULSAR_ROOT / 'src'
)

PULSAR_CONFIG_DIR = _get_env_or_default(
    'PULSAR_CONFIG_DIR',
    PULSAR_ROOT / '.config'
)

PULSAR_CACHE_DIR = _get_env_or_default(
    'PULSAR_CACHE_DIR',
    PULSAR_ROOT / '.cache'
)

PULSAR_DATA_DIR = _get_env_or_default(
    'PULSAR_DATA_DIR',
    PULSAR_ROOT / '.local' / 'share'
)

PULSAR_STATE_DIR = _get_env_or_default(
    'PULSAR_STATE_DIR',
    PULSAR_ROOT / '.local' / 'state'
)

PULSAR_VENV_DIR = _get_env_or_default(
    'PULSAR_VENV_DIR',
    PULSAR_ROOT / '.venv'
)


# ============================================================================
# XDG Base Directory Specification
# ============================================================================

XDG_CONFIG_HOME = _get_env_or_default(
    'XDG_CONFIG_HOME',
    PULSAR_ROOT / '.config'
)

XDG_CACHE_HOME = _get_env_or_default(
    'XDG_CACHE_HOME',
    PULSAR_ROOT / '.cache'
)

XDG_DATA_HOME = _get_env_or_default(
    'XDG_DATA_HOME',
    PULSAR_ROOT / '.local' / 'share'
)

XDG_STATE_HOME = _get_env_or_default(
    'XDG_STATE_HOME',
    PULSAR_ROOT / '.local' / 'state'
)


# ============================================================================
# UV (Python Package Manager) Directories
# ============================================================================

# UV directories default to Pulsar-managed locations

UV_TOOL_DIR = _get_env_or_default(
    'UV_TOOL_DIR',
    PULSAR_DATA_DIR / 'uv' / 'tools'
)

UV_PYTHON_INSTALL_DIR = _get_env_or_default(
    'UV_PYTHON_INSTALL_DIR',
    PULSAR_DATA_DIR / 'uv' / 'python'
)

UV_CACHE_DIR = _get_env_or_default(
    'UV_CACHE_DIR',
    PULSAR_CACHE_DIR / 'uv'
)


# ============================================================================
# Activation State Management
# ============================================================================

env_vars: dict[str, str] = {}
path_entries: list[str] = []
source_files: list[str] = []

def set_env(name: str, value: str):
    """Set an environment variable.

    Args:
        name: Environment variable name
        value: Environment variable value
    """

    assert name not in env_vars
    env_vars[name] = value

def add_to_path(directory: str):
    """Add a directory to PATH.

    Args:
        directory: Directory path to add to PATH
    """
    if directory not in path_entries:
        path_entries.append(directory)

def add_source_file(file_path: str):
    """Add a shell script file to be sourced during activation.

    Args:
        file_path: Path to the shell script file to source
    """
    if file_path not in source_files:
        source_files.append(file_path)
