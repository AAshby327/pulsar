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
from .bat import BatLinux, BatWindows


class FzfLinux(LinuxPackage):
    name = 'fzf'
    description = 'Command-line fuzzy finder'
    dependencies = [BatLinux]

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest fzf version from GitHub API"""
        try:
            url = "https://api.github.com/repos/junegunn/fzf/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Remove 'v' prefix from tag_name (e.g., "v0.55.0" -> "0.55.0")
                return data['tag_name'].lstrip('v')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 0.55.0")
            return "0.55.0"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if fzf is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['which', 'fzf'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if fzf is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'fzf'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of fzf"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'fzf'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "0.55.0 (brew)"
                match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("fzf environment activated")

        # Register fzf bash functions and aliases
        fzf_config = os.path.join(pulsar_env.PULSAR_CONFIG_DIR, 'fzf', 'fzf.bash')
        if os.path.exists(fzf_config):
            pulsar_env.add_source_file(fzf_config)
            cls.logger.info(f"Registered fzf config: {fzf_config}")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install fzf binary to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'fzf'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("fzf is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting fzf installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/junegunn/fzf/releases/download/v0.55.0/fzf-0.55.0-linux_amd64.tar.gz
        # or:     https://github.com/junegunn/fzf/releases/download/v0.55.0/fzf-0.55.0-linux_arm64.tar.gz
        if pulsar_env.ARCH == 'x86_64':
            arch_name = 'amd64'
        elif pulsar_env.ARCH == 'aarch64':
            arch_name = 'arm64'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"fzf-{version}-linux_{arch_name}.tar.gz"
        url = f"https://github.com/junegunn/fzf/releases/download/v{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"fzf-extract-{version}"

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

            # Find the fzf binary
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing fzf binary")

            fzf_binary = temp_extract_dir / "fzf"
            if not fzf_binary.exists():
                raise RuntimeError("Could not find fzf binary in archive")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy binary
            import shutil
            cls.logger.info(f"Installing fzf to {binary_path}")
            shutil.copy2(str(fzf_binary), str(binary_path))
            # Make binary executable
            binary_path.chmod(0o755)

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"fzf installed successfully to {binary_path}")

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
        """Uninstall fzf from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("fzf is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'fzf'

        try:
            if binary_path.exists():
                binary_path.unlink()
                cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise


class FzfWindows(WindowsPackage):
    name = 'fzf'
    description = 'Command-line fuzzy finder'
    dependencies = [BatWindows]

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest fzf version from GitHub API"""
        try:
            url = "https://api.github.com/repos/junegunn/fzf/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Remove 'v' prefix from tag_name (e.g., "v0.55.0" -> "0.55.0")
                return data['tag_name'].lstrip('v')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 0.55.0")
            return "0.55.0"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if fzf is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['where', 'fzf'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if fzf is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'fzf.exe'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of fzf"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'fzf.exe'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "0.55.0 (brew)"
                match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("fzf environment activated")

        # Register fzf PowerShell functions and configuration
        fzf_config = os.path.join(pulsar_env.PULSAR_CONFIG_DIR, 'fzf', 'fzf.ps1')
        if os.path.exists(fzf_config):
            pulsar_env.add_source_file(fzf_config)
            cls.logger.info(f"Registered fzf config: {fzf_config}")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install fzf to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'fzf.exe'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("fzf is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting fzf installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/junegunn/fzf/releases/download/v0.55.0/fzf-0.55.0-windows_amd64.zip
        # or:     https://github.com/junegunn/fzf/releases/download/v0.55.0/fzf-0.55.0-windows_arm64.zip
        if pulsar_env.ARCH == 'x86_64':
            arch_name = 'amd64'
        elif pulsar_env.ARCH == 'aarch64':
            arch_name = 'arm64'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"fzf-{version}-windows_{arch_name}.zip"
        url = f"https://github.com/junegunn/fzf/releases/download/v{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"fzf-extract-{version}"

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

            # Find the fzf binary
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing fzf binary")

            fzf_binary = temp_extract_dir / "fzf.exe"
            if not fzf_binary.exists():
                raise RuntimeError("Could not find fzf.exe in archive")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy binary
            import shutil
            cls.logger.info(f"Installing fzf to {binary_path}")
            shutil.copy2(str(fzf_binary), str(binary_path))

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"fzf installed successfully to {binary_path}")

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
        """Uninstall fzf from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("fzf is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'fzf.exe'

        try:
            if binary_path.exists():
                binary_path.unlink()
                cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
