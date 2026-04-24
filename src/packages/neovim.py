import os
import subprocess
import tarfile
import zipfile
import re
import json
import urllib.request
from pathlib import Path

from package_classes import LinuxPackage, WindowsPackage
import pulsar_env
from .ripgrep import RipgrepLinux, RipgrepWindows
from .fzf import FzfLinux, FzfWindows


class NeovimLinux(LinuxPackage):
    name = 'neovim'
    description = 'Hyperextensible Vim-based text editor'
    dependencies = [RipgrepLinux, FzfLinux]

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest neovim version from GitHub API"""
        try:
            url = "https://api.github.com/repos/neovim/neovim/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Remove 'v' prefix from tag_name (e.g., "v0.10.0" -> "0.10.0")
                return data['tag_name'].lstrip('v')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 0.12.2")
            return "0.12.2"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if neovim is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['which', 'nvim'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if neovim is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim' / 'bin' / 'nvim'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of neovim"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim' / 'bin' / 'nvim'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "NVIM v0.10.0"
                match = re.search(r'NVIM\s+v?(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("Neovim environment activated")

        # Add nvim bin subdirectory to PATH
        nvim_bin = os.path.join(pulsar_env.PULSAR_BIN_DIR, 'nvim', 'bin')
        if os.path.exists(nvim_bin):
            pulsar_env.add_to_path(nvim_bin)
            cls.logger.info(f"Added {nvim_bin} to PATH")

        # Set VIMRUNTIME to point to Pulsar's nvim runtime files
        runtime_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim' / 'share' / 'nvim' / 'runtime'
        if runtime_path.exists():
            pulsar_env.set_env('VIMRUNTIME', str(runtime_path))
            cls.logger.info(f"Set VIMRUNTIME to {runtime_path}")
        else:
            cls.logger.warning(f"Runtime path not found: {runtime_path}")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install neovim to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim'
        binary_path = bin_dir / 'bin' / 'nvim'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Neovim is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Neovim installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/neovim/neovim/releases/download/v0.12.2/nvim-linux-x86_64.tar.gz
        # or:     https://github.com/neovim/neovim/releases/download/v0.12.2/nvim-linux-arm64.tar.gz
        if pulsar_env.ARCH == 'x86_64':
            arch_name = 'x86_64'
        elif pulsar_env.ARCH == 'aarch64':
            arch_name = 'arm64'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"nvim-linux-{arch_name}.tar.gz"
        url = f"https://github.com/neovim/neovim/releases/download/v{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"neovim-extract-{version}"

        try:
            # Check if download is already cached
            download_cached = download_path.exists()

            if download_cached and not refresh_cache:
                # Use cached download
                cls.set_status("Using cached download", "cyan")
                cls.logger.info(f"Using cached download from {download_path}")
            else:
                # Download fresh or refresh cache
                if download_cached and refresh_cache:
                    cls.logger.info(f"Refreshing cache, removing old download")
                    download_path.unlink()

                cls.set_status("Downloading", "yellow")
                cls.logger.info(f"Downloading from GitHub releases")

                # Ensure cache directory exists
                cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

                cls.download(url, download_path)

            # Extract to temporary directory
            cls.set_status("Extracting", "cyan")
            cls.logger.info(f"Extracting archive")

            # Clean temp directory if it exists
            if temp_extract_dir.exists():
                import shutil
                shutil.rmtree(temp_extract_dir)

            temp_extract_dir.mkdir(parents=True, exist_ok=True)

            # Extract tar.gz file
            with tarfile.open(download_path, 'r:gz') as tar:
                tar.extractall(temp_extract_dir)

            # Find the nvim directory
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing neovim")

            extract_dir_name = f"nvim-linux-{arch_name}"
            nvim_extracted_dir = temp_extract_dir / extract_dir_name
            if not nvim_extracted_dir.exists():
                raise RuntimeError("Could not find nvim directory in archive")

            # Verify binary exists
            nvim_binary = nvim_extracted_dir / "bin" / "nvim"
            if not nvim_binary.exists():
                raise RuntimeError("Could not find nvim binary in archive")

            # Remove old installation if it exists
            import shutil
            if bin_dir.exists():
                cls.logger.info(f"Removing old installation at {bin_dir}")
                shutil.rmtree(bin_dir)

            # Copy the entire nvim directory structure
            cls.logger.info(f"Installing nvim to {bin_dir}")
            shutil.copytree(str(nvim_extracted_dir), str(bin_dir))

            # Make binary executable
            binary_path.chmod(0o755)

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"Neovim installed successfully to {binary_path}")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            # Cleanup on error
            if temp_extract_dir.exists():
                import shutil
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            raise

    @classmethod
    def uninstall(cls):
        """Uninstall neovim from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Neovim is not installed with Pulsar")
            return

        nvim_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim'

        try:
            if nvim_dir.exists():
                import shutil
                shutil.rmtree(nvim_dir)
                cls.logger.info(f"Removed {nvim_dir}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise


class NeovimWindows(WindowsPackage):
    name = 'neovim'
    description = 'Hyperextensible Vim-based text editor'
    dependencies = [RipgrepWindows, FzfWindows]

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest neovim version from GitHub API"""
        try:
            url = "https://api.github.com/repos/neovim/neovim/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Remove 'v' prefix from tag_name (e.g., "v0.10.0" -> "0.10.0")
                return data['tag_name'].lstrip('v')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 0.12.2")
            return "0.12.2"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if neovim is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['where', 'nvim'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if neovim is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim' / 'bin' / 'nvim.exe'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of neovim"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim' / 'bin' / 'nvim.exe'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "NVIM v0.10.0"
                match = re.search(r'NVIM\s+v?(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("Neovim environment activated")

        # Add nvim bin subdirectory to PATH
        nvim_bin = os.path.join(pulsar_env.PULSAR_BIN_DIR, 'nvim', 'bin')
        if os.path.exists(nvim_bin):
            pulsar_env.add_to_path(nvim_bin)
            cls.logger.info(f"Added {nvim_bin} to PATH")

        # Set VIMRUNTIME to point to Pulsar's nvim runtime files
        runtime_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim' / 'share' / 'nvim' / 'runtime'
        if runtime_path.exists():
            pulsar_env.set_env('VIMRUNTIME', str(runtime_path))
            cls.logger.info(f"Set VIMRUNTIME to {runtime_path}")
        else:
            cls.logger.warning(f"Runtime path not found: {runtime_path}")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install neovim to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim'
        binary_path = bin_dir / 'bin' / 'nvim.exe'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Neovim is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Neovim installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/neovim/neovim/releases/download/v0.12.2/nvim-win64.zip
        # or:     https://github.com/neovim/neovim/releases/download/v0.12.2/nvim-win-arm64.zip
        if pulsar_env.ARCH == 'x86_64':
            arch_name = 'win64'
        elif pulsar_env.ARCH == 'aarch64':
            arch_name = 'win-arm64'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"nvim-{arch_name}.zip"
        url = f"https://github.com/neovim/neovim/releases/download/v{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"neovim-extract-{version}"

        try:
            # Check if download is already cached
            download_cached = download_path.exists()

            if download_cached and not refresh_cache:
                # Use cached download
                cls.set_status("Using cached download", "cyan")
                cls.logger.info(f"Using cached download from {download_path}")
            else:
                # Download fresh or refresh cache
                if download_cached and refresh_cache:
                    cls.logger.info(f"Refreshing cache, removing old download")
                    download_path.unlink()

                cls.set_status("Downloading", "yellow")
                cls.logger.info(f"Downloading from GitHub releases")

                # Ensure cache directory exists
                cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

                cls.download(url, download_path)

            # Extract to temporary directory
            cls.set_status("Extracting", "cyan")
            cls.logger.info(f"Extracting archive")

            # Clean temp directory if it exists
            if temp_extract_dir.exists():
                import shutil
                shutil.rmtree(temp_extract_dir)

            temp_extract_dir.mkdir(parents=True, exist_ok=True)

            # Extract zip file
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)

            # Find the nvim directory
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing neovim")

            extract_dir_name = f"nvim-{arch_name}"
            nvim_extracted_dir = temp_extract_dir / extract_dir_name
            if not nvim_extracted_dir.exists():
                raise RuntimeError("Could not find nvim directory in archive")

            # Verify binary exists
            nvim_binary = nvim_extracted_dir / "bin" / "nvim.exe"
            if not nvim_binary.exists():
                raise RuntimeError("Could not find nvim.exe in archive")

            # Remove old installation if it exists
            import shutil
            if bin_dir.exists():
                cls.logger.info(f"Removing old installation at {bin_dir}")
                shutil.rmtree(bin_dir)

            # Copy the entire nvim directory structure
            cls.logger.info(f"Installing nvim to {bin_dir}")
            shutil.copytree(str(nvim_extracted_dir), str(bin_dir))

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"Neovim installed successfully to {binary_path}")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            # Cleanup on error
            if temp_extract_dir.exists():
                import shutil
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            raise

    @classmethod
    def uninstall(cls):
        """Uninstall neovim from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Neovim is not installed with Pulsar")
            return

        nvim_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'nvim'

        try:
            if nvim_dir.exists():
                import shutil
                shutil.rmtree(nvim_dir)
                cls.logger.info(f"Removed {nvim_dir}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
