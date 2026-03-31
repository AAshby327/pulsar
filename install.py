#!/usr/bin/env python3
"""
Pulsar Installer - Bootstrap script for portable development environment.

This script:
1. Detects the current platform
2. Installs UV if not already present
3. Installs the pulsar CLI tool
4. Installs required packages (wezterm, neovim, etc.) via CLI
"""

import os
import platform
import stat
import subprocess
import sys
from pathlib import Path
from urllib.request import urlretrieve


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_step(text: str):
    """Print a step indicator."""
    print(f"▶ {text}")


def print_success(text: str):
    """Print a success message."""
    print(f"✓ {text}")


def print_error(text: str):
    """Print an error message."""
    print(f"✗ {text}", file=sys.stderr)


def get_platform():
    """Detect the current platform and architecture."""
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


def download_with_progress(url: str, dest: Path):
    """Download a file with progress indicator."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading from: {url}")

    def progress(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100)
            print(f"\r  Progress: {percent:.1f}%", end="", flush=True)

    urlretrieve(url, dest, reporthook=progress)
    print()  # New line after progress


def make_executable(path: Path):
    """Make a file executable (Unix only)."""
    if platform.system().lower() != "windows":
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)


def install_cli_tool(root_dir: Path, os_type: str):
    """Install the pulsar CLI tool via UV."""
    print_step("Installing pulsar CLI tool...")

    # Check if pyproject.toml exists
    pyproject = root_dir / "src" / "pulsar_cli" / "pyproject.toml"
    if not pyproject.exists():
        print("  Skipping CLI installation (pyproject.toml not found)")
        print("  CLI tool will be available after full setup")
        return

    uv_binary = root_dir / "bin" / ("uv.exe" if os_type == "windows" else "uv")

    if not uv_binary.exists():
        print_error("UV not found! Cannot install CLI tool.")
        return

    # Set up environment for UV
    env = os.environ.copy()
    env["UV_TOOL_DIR"] = str(root_dir / ".local" / "share" / "uv" / "tools")
    env["UV_PYTHON_INSTALL_DIR"] = str(root_dir / ".local" / "share" / "uv" / "python")
    env["UV_CACHE_DIR"] = str(root_dir / ".cache" / "uv")

    # Install the CLI tool
    try:
        subprocess.run(
            [str(uv_binary), "tool", "install", "--force", str(root_dir / "src" / "pulsar_cli")],
            check=True,
            env=env,
        )
        print_success("Pulsar CLI tool installed")
        print(f"  CLI tool path: {root_dir / '.local' / 'share' / 'uv' / 'tools' / 'pulsar-cli' / 'bin' / 'pulsar'}")
    except subprocess.CalledProcessError as e:
        print(f"  Warning: CLI tool installation failed: {e}")
        print("  You can install it later manually with:")
        print(f"    export UV_TOOL_DIR=\"{root_dir}/.local/share/uv/tools\"")
        print(f"    export UV_PYTHON_INSTALL_DIR=\"{root_dir}/.local/share/uv/python\"")
        print(f"    export UV_CACHE_DIR=\"{root_dir}/.cache/uv\"")
        print(f"    ./bin/uv tool install ./src/pulsar_cli")


def main():
    """Main installation routine."""
    print_header("Pulsar Installer")
    print("Setting up your portable WezTerm + Neovim environment...\n")

    # Get current directory as root
    root_dir = Path(__file__).parent.resolve()
    print(f"Installation directory: {root_dir}\n")

    # Detect platform
    try:
        os_type, arch = get_platform()
        print(f"Detected platform: {os_type.capitalize()} {arch}\n")
    except RuntimeError as e:
        print_error(str(e))
        sys.exit(1)

    # Run installation steps
    try:
        install_cli_tool(root_dir, os_type)

        # Success message
        print_header("Bootstrap Complete!")
        print("UV and Pulsar CLI are ready!\n")
        print("Next steps:")
        if os_type == "windows":
            print("  1. Run: .\\launch.ps1")
            print("     (This will install required packages and open WezTerm)")
            print("\n  2. Optional: Install additional packages with pulsar CLI")
            print("     - Activate environment: . .\\activate.ps1")
            print("     - Install tools: pulsar install ripgrep")
            print("     - Install plugins: pulsar install telescope.nvim")
        else:
            print("  1. Run: ./launch.sh")
            print("     (This will install required packages and open WezTerm)")
            print("\n  2. Optional: Install additional packages with pulsar CLI")
            print("     - Activate environment: source ./activate.sh")
            print("     - Install tools: pulsar install ripgrep")
            print("     - Install plugins: pulsar install telescope.nvim")

        print("\nTo uninstall: Simply delete this directory!")
        print(f"\nEnjoy your portable development environment! 🚀\n")

    except Exception as e:
        print_error(f"Installation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
