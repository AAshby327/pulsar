"""Platform and architecture detection utilities."""

import platform
from typing import Tuple


def get_platform() -> Tuple[str, str]:
    """
    Detect the current platform and architecture.

    Returns:
        Tuple of (os_type, architecture)
        - os_type: "linux", "windows", or "macos"
        - architecture: "x86_64" or "aarch64"

    Raises:
        RuntimeError: If platform is unsupported
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize OS type
    if system == "linux":
        os_type = "linux"
    elif system == "windows":
        os_type = "windows"
    elif system == "darwin":
        os_type = "macos"
    else:
        raise RuntimeError(f"Unsupported operating system: {system}")

    # Normalize architecture
    if machine in ["x86_64", "amd64", "x64"]:
        arch = "x86_64"
    elif machine in ["aarch64", "arm64"]:
        arch = "aarch64"
    else:
        raise RuntimeError(f"Unsupported architecture: {machine}")

    return os_type, arch


def get_platform_string() -> str:
    """
    Get a human-readable platform string.

    Returns:
        String like "Linux x86_64" or "Windows x86_64"
    """
    os_type, arch = get_platform()
    os_name = os_type.capitalize()
    return f"{os_name} {arch}"


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system().lower() == "windows"


def is_linux() -> bool:
    """Check if running on Linux."""
    return platform.system().lower() == "linux"


def is_macos() -> bool:
    """Check if running on macOS."""
    return platform.system().lower() == "darwin"


def get_exe_suffix() -> str:
    """
    Get the executable suffix for the current platform.

    Returns:
        ".exe" on Windows, "" on Unix-like systems
    """
    return ".exe" if is_windows() else ""
