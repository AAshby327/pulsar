"""
Pulsar Environment Configuration

This module detects the operating system, architecture, and sets up environment
variables with sensible defaults for pulsar package management.

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
if not 'PULSAR_SHELL' in os.environ:
    raise EnvironmentError("PULSAR_SHELL environment variable not set.")

SHELL = os.environ['PULSAR_SHELL']


# ============================================================================
# Helper Functions
# ============================================================================

def _get_psr_env(var_name: str) -> str:
    try:
        return os.environ[var_name]
    except KeyError:
        raise EnvironmentError(f"Necessary pulsar environment variable is not set: {var_name}")


def remove_directories(*paths: pathlib.Path | str) -> None:
    for path in paths:
        print("Removing path: ", path)


# ============================================================================
# Pulsar Root Directory
# ============================================================================

# PULSAR_ROOT: Base directory for pulsar
# Default: Current working directory
_pulsar_root_str = os.environ.get('PULSAR_ROOT') or os.getcwd()
PULSAR_ROOT = pathlib.Path(_pulsar_root_str).resolve()


# ============================================================================
# Pulsar Directories
# ============================================================================

# All pulsar directories default to subdirectories of PULSAR_ROOT
PULSAR_BIN_DIR =    pathlib.Path(_get_psr_env('PULSAR_BIN_DIR'))
PULSAR_SRC_DIR =    pathlib.Path(_get_psr_env('PULSAR_SRC_DIR'))
PULSAR_CONFIG_DIR = pathlib.Path(_get_psr_env('PULSAR_CONFIG_DIR'))
PULSAR_CACHE_DIR =  pathlib.Path(_get_psr_env('PULSAR_CACHE_DIR'))
PULSAR_DATA_DIR =   pathlib.Path(_get_psr_env('PULSAR_DATA_DIR'))
PULSAR_STATE_DIR =  pathlib.Path(_get_psr_env('PULSAR_STATE_DIR'))
PULSAR_VENV_DIR =   pathlib.Path(_get_psr_env('PULSAR_VENV_DIR'))


# ============================================================================
# XDG Base Directory Specification
# ============================================================================

XDG_CONFIG_HOME =   pathlib.Path(_get_psr_env('XDG_CONFIG_HOME'))
XDG_CACHE_HOME =    pathlib.Path(_get_psr_env('XDG_CACHE_HOME'))
XDG_DATA_HOME =     pathlib.Path(_get_psr_env('XDG_DATA_HOME'))
XDG_STATE_HOME =    pathlib.Path(_get_psr_env('XDG_STATE_HOME'))


# ============================================================================
# UV (Python Package Manager) Directories
# ============================================================================

UV_TOOL_DIR =           pathlib.Path(_get_psr_env('UV_TOOL_DIR'))
UV_PYTHON_INSTALL_DIR = pathlib.Path(_get_psr_env('UV_PYTHON_INSTALL_DIR'))
UV_CACHE_DIR =          pathlib.Path(_get_psr_env('UV_CACHE_DIR'))


# ============================================================================
# Activation State Management
# ============================================================================

PULSAR_SHELL_FILE = pathlib.Path(_get_psr_env('PULSAR_SHELL_FILE'))

env_vars: dict[str, str] = {}
path_entries: list[str] = []
source_files: list[str] = []

def set_env(name: str, value: str):
    """Set an environment variable.

    Args:
        name: Environment variable name
        value: Environment variable value
    """

    # Reserved pulsar environment variables
    reserved_vars = {
        'PULSAR_ROOT', 'PULSAR_BIN_DIR', 'PULSAR_SRC_DIR', 'PULSAR_CONFIG_DIR',
        'PULSAR_CACHE_DIR', 'PULSAR_DATA_DIR', 'PULSAR_STATE_DIR', 'PULSAR_VENV_DIR',
        'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME',
        'UV_TOOL_DIR', 'UV_PYTHON_INSTALL_DIR', 'UV_CACHE_DIR',
        'PULSAR_SHELL_FILE'
    }

    assert name not in reserved_vars
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

    path = pathlib.Path(file_path)

    assert path.is_file()
    assert path.exists()
    if SHELL == 'powershell':
        assert path.suffix == '.ps1'

    if file_path not in source_files:
        source_files.append(file_path)
