import subprocess
import gzip
import shutil
import re
import json
import urllib.request
from pathlib import Path

from package_classes import LinuxPackage, WindowsPackage
import pulsar_env


class TreesitterLinux(LinuxPackage):
    name = 'tree-sitter'
    description = 'Incremental parsing system for programming tools'
    dependencies = []

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest tree-sitter version from GitHub API"""
        try:
            url = "https://api.github.com/repos/tree-sitter/tree-sitter/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Version format includes 'v' prefix (e.g., "v0.24.6")
                return data['tag_name']
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to v0.24.6")
            return "v0.24.6"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if tree-sitter is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['which', 'tree-sitter'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if tree-sitter is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'tree-sitter'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of tree-sitter"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'tree-sitter'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "tree-sitter 0.24.6"
                match = re.search(r'tree-sitter\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("tree-sitter environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install tree-sitter CLI to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'tree-sitter'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("tree-sitter is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting tree-sitter installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/tree-sitter/tree-sitter/releases/download/v0.24.6/tree-sitter-linux-x64.gz
        # or:     https://github.com/tree-sitter/tree-sitter/releases/download/v0.24.6/tree-sitter-linux-arm64.gz
        if pulsar_env.ARCH == 'x86_64':
            arch_suffix = 'x64'
        elif pulsar_env.ARCH == 'aarch64':
            arch_suffix = 'arm64'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"tree-sitter-linux-{arch_suffix}.gz"
        url = f"https://github.com/tree-sitter/tree-sitter/releases/download/{version}/{filename}"

        download_path = cls.CACHE_DIR / filename

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

            # Extract gzip file directly to bin directory
            cls.set_status("Installing", "cyan")
            cls.logger.info("Extracting and installing tree-sitter binary")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Extract gzip file (single binary inside)
            with gzip.open(download_path, 'rb') as gz_file:
                with open(binary_path, 'wb') as out_file:
                    shutil.copyfileobj(gz_file, out_file)

            # Make binary executable
            binary_path.chmod(0o755)

            cls.set_status("Complete", "green")
            cls.logger.info(f"tree-sitter installed successfully to {binary_path}")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            # Cleanup on error
            if binary_path.exists():
                binary_path.unlink(missing_ok=True)
            raise

    @classmethod
    def uninstall(cls):
        """Uninstall tree-sitter from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("tree-sitter is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'tree-sitter'

        try:
            if binary_path.exists():
                binary_path.unlink()
                cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise


class TreesitterWindows(WindowsPackage):
    name = 'tree-sitter'
    description = 'Incremental parsing system for programming tools'
    dependencies = []

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest tree-sitter version from GitHub API"""
        try:
            url = "https://api.github.com/repos/tree-sitter/tree-sitter/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Version format includes 'v' prefix (e.g., "v0.24.6")
                return data['tag_name']
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to v0.24.6")
            return "v0.24.6"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if tree-sitter is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['where', 'tree-sitter'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if tree-sitter is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'tree-sitter.exe'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of tree-sitter"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'tree-sitter.exe'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "tree-sitter 0.24.6"
                match = re.search(r'tree-sitter\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("tree-sitter environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install tree-sitter CLI to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'tree-sitter.exe'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("tree-sitter is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting tree-sitter installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/tree-sitter/tree-sitter/releases/download/v0.24.6/tree-sitter-windows-x64.gz
        # or:     https://github.com/tree-sitter/tree-sitter/releases/download/v0.24.6/tree-sitter-windows-arm64.gz
        if pulsar_env.ARCH == 'x86_64':
            arch_suffix = 'x64'
        elif pulsar_env.ARCH == 'aarch64':
            arch_suffix = 'arm64'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"tree-sitter-windows-{arch_suffix}.gz"
        url = f"https://github.com/tree-sitter/tree-sitter/releases/download/{version}/{filename}"

        download_path = cls.CACHE_DIR / filename

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

            # Extract gzip file directly to bin directory
            cls.set_status("Installing", "cyan")
            cls.logger.info("Extracting and installing tree-sitter binary")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Extract gzip file (single binary inside)
            with gzip.open(download_path, 'rb') as gz_file:
                with open(binary_path, 'wb') as out_file:
                    shutil.copyfileobj(gz_file, out_file)

            cls.set_status("Complete", "green")
            cls.logger.info(f"tree-sitter installed successfully to {binary_path}")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            # Cleanup on error
            if binary_path.exists():
                binary_path.unlink(missing_ok=True)
            raise

    @classmethod
    def uninstall(cls):
        """Uninstall tree-sitter from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("tree-sitter is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'tree-sitter.exe'

        try:
            if binary_path.exists():
                binary_path.unlink()
                cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
