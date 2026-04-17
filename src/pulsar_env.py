"""
Pulsar Environment Configuration

This module detects the operating system, architecture, and sets up environment
variables with sensible defaults for Pulsar package management.

All variables use environment variables if set, otherwise fall back to defaults.
"""

import os
import typing
import platform
from pathlib import Path


# ============================================================================
# System Detection
# ============================================================================

OS: typing.Literal['linux', 'windows']
ARCH: typing.Literal['x86_64', 'aarch64']

# Detect operating system
OS = platform.system().lower()
if OS not in ['linux', 'windows']:
    raise RuntimeError(f"Unsupported operating system: {OS}")

# Detect architecture
machine = platform.machine().lower()
if machine in ['x86_64', 'amd64', 'x64']:
    ARCH = 'x86_64'
elif machine in ['aarch64', 'arm64']:
    ARCH = 'aarch64'
else:
    raise RuntimeError(f"Unsupported architecture: {machine}")


# ============================================================================
# Helper Functions
# ============================================================================

def _get_env_or_default(var_name: str, default_path: str) -> str:
    """Get environment variable or return default path."""
    return os.environ.get(var_name) or default_path


# ============================================================================
# Pulsar Root Directory
# ============================================================================

# PULSAR_ROOT: Base directory for Pulsar
# Default: Current working directory
PULSAR_ROOT = os.environ.get('PULSAR_ROOT') or os.getcwd()
PULSAR_ROOT = str(Path(PULSAR_ROOT).resolve())


# ============================================================================
# Pulsar Directories
# ============================================================================

# All Pulsar directories default to subdirectories of PULSAR_ROOT

PULSAR_BIN_DIR = _get_env_or_default(
    'PULSAR_BIN_DIR',
    os.path.join(PULSAR_ROOT, 'bin')
)

PULSAR_SRC_DIR = _get_env_or_default(
    'PULSAR_SRC_DIR',
    os.path.join(PULSAR_ROOT, 'src')
)

PULSAR_CONFIG_DIR = _get_env_or_default(
    'PULSAR_CONFIG_DIR',
    os.path.join(PULSAR_ROOT, '.config')
)

PULSAR_CACHE_DIR = _get_env_or_default(
    'PULSAR_CACHE_DIR',
    os.path.join(PULSAR_ROOT, '.cache')
)

PULSAR_DATA_DIR = _get_env_or_default(
    'PULSAR_DATA_DIR',
    os.path.join(PULSAR_ROOT, '.local', 'share')
)

PULSAR_STATE_DIR = _get_env_or_default(
    'PULSAR_STATE_DIR',
    os.path.join(PULSAR_ROOT, '.local', 'state')
)


# ============================================================================
# XDG Base Directory Specification
# ============================================================================

# Standard Linux/Unix directory locations
# See: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

HOME = os.path.expanduser('~')

XDG_CONFIG_HOME = _get_env_or_default(
    'XDG_CONFIG_HOME',
    os.path.join(HOME, '.config')
)

XDG_CACHE_HOME = _get_env_or_default(
    'XDG_CACHE_HOME',
    os.path.join(HOME, '.cache')
)

XDG_DATA_HOME = _get_env_or_default(
    'XDG_DATA_HOME',
    os.path.join(HOME, '.local', 'share')
)

XDG_STATE_HOME = _get_env_or_default(
    'XDG_STATE_HOME',
    os.path.join(HOME, '.local', 'state')
)


# ============================================================================
# UV (Python Package Manager) Directories
# ============================================================================

# UV directories default to Pulsar-managed locations

UV_TOOL_DIR = _get_env_or_default(
    'UV_TOOL_DIR',
    os.path.join(PULSAR_DATA_DIR, 'uv', 'tools')
)

UV_PYTHON_INSTALL_DIR = _get_env_or_default(
    'UV_PYTHON_INSTALL_DIR',
    os.path.join(PULSAR_DATA_DIR, 'uv', 'python')
)

UV_CACHE_DIR = _get_env_or_default(
    'UV_CACHE_DIR',
    os.path.join(PULSAR_CACHE_DIR, 'uv')
)


# ============================================================================
# Activation Variables
# ============================================================================

# Variables to export when activating Pulsar environment
ACTIVATION_VARS: dict[str, str] = {}