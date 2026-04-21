import subprocess
import tarfile
import zipfile
import re
import json
import urllib.request
from pathlib import Path

from package_classes import LinuxPackage, WindowsPackage
import pulsar_env


class LazygitLinux(LinuxPackage):
    name = 'lazygit'
    description = 'Simple terminal UI for git commands'
    dependencies = []

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest lazygit version from GitHub API"""
        try:
            url = "https://api.github.com/repos/jesseduffield/lazygit/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Remove 'v' prefix from tag_name (e.g., "v0.61.1" -> "0.61.1")
                return data['tag_name'].lstrip('v')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 0.40.2")
            return "0.40.2"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if lazygit is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['which', 'lazygit'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if lazygit is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'lazygit'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of lazygit"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'lazygit'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "version=0.40.2"
                match = re.search(r'version[=\s]+v?(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("Lazygit environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install lazygit binary to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'lazygit'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Lazygit is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Lazygit installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL
        # Format: https://github.com/jesseduffield/lazygit/releases/download/v0.40.2/lazygit_0.40.2_Linux_x86_64.tar.gz
        filename = f"lazygit_{version}_Linux_x86_64.tar.gz"
        url = f"https://github.com/jesseduffield/lazygit/releases/download/v{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"lazygit-extract-{version}"

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

            # Find the lazygit binary
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing lazygit binary")

            lazygit_binary = temp_extract_dir / "lazygit"
            if not lazygit_binary.exists():
                raise RuntimeError("Could not find lazygit binary in archive")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy binary
            import shutil
            cls.logger.info(f"Installing lazygit to {binary_path}")
            shutil.copy2(str(lazygit_binary), str(binary_path))
            # Make binary executable
            binary_path.chmod(0o755)

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"Lazygit installed successfully to {binary_path}")

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
        """Uninstall lazygit from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Lazygit is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'lazygit'

        try:
            if binary_path.exists():
                binary_path.unlink()
                cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise


class LazygitWindows(WindowsPackage):
    name = 'lazygit'
    description = 'Simple terminal UI for git commands'
    dependencies = []  # Set in setup_dependencies()

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest lazygit version from GitHub API"""
        try:
            url = "https://api.github.com/repos/jesseduffield/lazygit/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Remove 'v' prefix from tag_name (e.g., "v0.61.1" -> "0.61.1")
                return data['tag_name'].lstrip('v')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 0.40.2")
            return "0.40.2"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if lazygit is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['where', 'lazygit'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if lazygit is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'lazygit.exe'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of lazygit"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'lazygit.exe'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "version=0.40.2"
                match = re.search(r'version[=\s]+v?(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("Lazygit environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install lazygit to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'lazygit.exe'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Lazygit is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Lazygit installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL
        # Format: https://github.com/jesseduffield/lazygit/releases/download/v0.40.2/lazygit_0.40.2_Windows_x86_64.zip
        filename = f"lazygit_{version}_Windows_x86_64.zip"
        url = f"https://github.com/jesseduffield/lazygit/releases/download/v{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"lazygit-extract-{version}"

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

            # Find the lazygit binary
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing lazygit binary")

            lazygit_binary = temp_extract_dir / "lazygit.exe"
            if not lazygit_binary.exists():
                raise RuntimeError("Could not find lazygit.exe in archive")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy binary
            import shutil
            cls.logger.info(f"Installing lazygit to {binary_path}")
            shutil.copy2(str(lazygit_binary), str(binary_path))

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"Lazygit installed successfully to {binary_path}")

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
        """Uninstall lazygit from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Lazygit is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'lazygit.exe'

        try:
            if binary_path.exists():
                binary_path.unlink()
                cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise

