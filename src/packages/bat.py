import subprocess
import tarfile
import zipfile
import re
import json
import urllib.request
from pathlib import Path

from package_classes import LinuxPackage, WindowsPackage
import pulsar_env


class BatLinux(LinuxPackage):
    name = 'bat'
    description = 'A cat clone with syntax highlighting and Git integration'
    dependencies = []

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest bat version from GitHub API"""
        try:
            url = "https://api.github.com/repos/sharkdp/bat/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Tag format is "v0.26.1"
                return data['tag_name']
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to v0.26.1")
            return "v0.26.1"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if bat is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['which', 'bat'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if bat is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'bat'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of bat"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'bat'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "bat 0.26.1"
                match = re.search(r'bat\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("bat environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install bat binary to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'bat'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("bat is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting bat installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        # Ensure version has 'v' prefix
        if not version.startswith('v'):
            version = f'v{version}'

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/sharkdp/bat/releases/download/v0.26.1/bat-v0.26.1-x86_64-unknown-linux-musl.tar.gz
        # or:     https://github.com/sharkdp/bat/releases/download/v0.26.1/bat-v0.26.1-aarch64-unknown-linux-gnu.tar.gz
        if pulsar_env.ARCH == 'x86_64':
            arch_target = 'x86_64-unknown-linux-musl'
        elif pulsar_env.ARCH == 'aarch64':
            arch_target = 'aarch64-unknown-linux-gnu'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"bat-{version}-{arch_target}.tar.gz"
        url = f"https://github.com/sharkdp/bat/releases/download/{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"bat-extract-{version}"

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

            # Find the bat binary
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing bat binary")

            # The archive extracts to bat-{version}-{arch_target}/bat
            bat_binary = temp_extract_dir / f"bat-{version}-{arch_target}" / "bat"
            if not bat_binary.exists():
                raise RuntimeError("Could not find bat binary in archive")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy binary
            import shutil
            cls.logger.info(f"Installing bat to {binary_path}")
            shutil.copy2(str(bat_binary), str(binary_path))
            # Make binary executable
            binary_path.chmod(0o755)

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"bat installed successfully to {binary_path}")

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
        """Uninstall bat from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("bat is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'bat'

        try:
            if binary_path.exists():
                binary_path.unlink()
                cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise


class BatWindows(WindowsPackage):
    name = 'bat'
    description = 'A cat clone with syntax highlighting and Git integration'
    dependencies = []

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest bat version from GitHub API"""
        try:
            url = "https://api.github.com/repos/sharkdp/bat/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Tag format is "v0.26.1"
                return data['tag_name']
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to v0.26.1")
            return "v0.26.1"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if bat is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['where', 'bat'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if bat is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'bat.exe'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of bat"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'bat.exe'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "bat 0.26.1"
                match = re.search(r'bat\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("bat environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install bat to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'bat.exe'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("bat is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting bat installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        # Ensure version has 'v' prefix
        if not version.startswith('v'):
            version = f'v{version}'

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/sharkdp/bat/releases/download/v0.26.1/bat-v0.26.1-x86_64-pc-windows-msvc.zip
        # or:     https://github.com/sharkdp/bat/releases/download/v0.26.1/bat-v0.26.1-aarch64-pc-windows-msvc.zip
        if pulsar_env.ARCH == 'x86_64':
            arch_target = 'x86_64-pc-windows-msvc'
        elif pulsar_env.ARCH == 'aarch64':
            arch_target = 'aarch64-pc-windows-msvc'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"bat-{version}-{arch_target}.zip"
        url = f"https://github.com/sharkdp/bat/releases/download/{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"bat-extract-{version}"

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

            # Find the bat binary
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing bat binary")

            # The archive extracts to bat-{version}-{arch_target}/bat.exe
            bat_binary = temp_extract_dir / f"bat-{version}-{arch_target}" / "bat.exe"
            if not bat_binary.exists():
                raise RuntimeError("Could not find bat.exe in archive")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy binary
            import shutil
            cls.logger.info(f"Installing bat to {binary_path}")
            shutil.copy2(str(bat_binary), str(binary_path))

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"bat installed successfully to {binary_path}")

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
        """Uninstall bat from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("bat is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'bat.exe'

        try:
            if binary_path.exists():
                binary_path.unlink()
                cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
