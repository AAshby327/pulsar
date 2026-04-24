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

# class ActivationState:
#     """Accumulates environment changes for shell activation scripts."""

#     def __init__(self):
#         self.env_vars: dict[str, str] = {}
#         self.path_entries: list[str] = []
#         self.aliases: dict[str, str] = {}

#     def set_env(self, name: str, value: str):
#         """Set an environment variable.

#         Args:
#             name: Environment variable name
#             value: Environment variable value
#         """
#         self.env_vars[name] = value

#     def add_to_path(self, directory: str):
#         """Add a directory to PATH.

#         Args:
#             directory: Directory path to add to PATH
#         """
#         if directory not in self.path_entries:
#             self.path_entries.append(directory)

#     def add_alias(self, name: str, command: str):
#         """Add a shell alias.

#         Args:
#             name: Alias name
#             command: Command to alias
#         """
#         self.aliases[name] = command

#     def generate_bash_script(self) -> str:
#         """Generate bash activation script.

#         Returns:
#             Bash script as a string
#         """
#         lines = []

#         # Environment variables
#         for name, value in self.env_vars.items():
#             # Escape quotes in value
#             escaped_value = value.replace('"', '\\"')
#             lines.append(f'export {name}="{escaped_value}"')

#         # PATH additions (prepend to PATH)
#         for path in self.path_entries:
#             escaped_path = path.replace('"', '\\"')
#             lines.append(f'export PATH="{escaped_path}:$PATH"')

#         # Aliases
#         for name, command in self.aliases.items():
#             escaped_command = command.replace('"', '\\"')
#             lines.append(f'alias {name}="{escaped_command}"')

#         return '\n'.join(lines)

#     def generate_powershell_script(self) -> str:
#         """Generate PowerShell activation script.

#         Returns:
#             PowerShell script as a string
#         """
#         lines = []

#         # Environment variables
#         for name, value in self.env_vars.items():
#             # Escape quotes in value for PowerShell
#             escaped_value = value.replace('"', '`"')
#             lines.append(f'$env:{name} = "{escaped_value}"')

#         # PATH additions (prepend to PATH)
#         for path in self.path_entries:
#             escaped_path = path.replace('"', '`"')
#             lines.append(f'$env:PATH = "{escaped_path};$env:PATH"')

#         # Aliases (PowerShell aliases are more limited)
#         for name, command in self.aliases.items():
#             # For simple commands, use Set-Alias
#             # For complex commands, we'd need to create functions instead
#             escaped_command = command.replace('"', '`"')
#             lines.append(f'Set-Alias -Name {name} -Value "{escaped_command}"')

#         return '\n'.join(lines)


# # Global activation state instance
# _activation_state = ActivationState()


# def get_activation_state() -> ActivationState:
#     """Get the current activation state.

#     Returns:
#         The global ActivationState instance
#     """
#     return _activation_state


# def reset_activation_state():
#     """Reset the activation state to a clean slate."""
#     global _activation_state
#     _activation_state = ActivationState()

