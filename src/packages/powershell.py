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


class PowerShellLinux(LinuxPackage):
    name = 'powershell'
    description = 'Cross-platform task automation and configuration management framework'

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest PowerShell version from GitHub API"""
        try:
            url = "https://api.github.com/repos/PowerShell/PowerShell/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Remove 'v' prefix from tag_name (e.g., "v7.6.0" -> "7.6.0")
                return data['tag_name'].lstrip('v')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 7.4.6")
            return "7.4.6"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if PowerShell is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['which', 'pwsh'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if PowerShell is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'powershell' / 'pwsh'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of PowerShell"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'powershell' / 'pwsh'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "PowerShell 7.4.0"
                match = re.search(r'PowerShell\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("PowerShell environment activated")

        # Add PowerShell bin subdirectory to PATH
        powershell_bin = os.path.join(pulsar_env.PULSAR_BIN_DIR, 'powershell')
        current_path = os.environ.get('PATH', '')
        if powershell_bin not in current_path:
            pulsar_env.set_env('PATH', f"{powershell_bin}:{current_path}")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install PowerShell to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'powershell'
        binary_path = bin_dir / 'pwsh'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("PowerShell is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting PowerShell installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Determine architecture
        arch = pulsar_env.ARCH
        if arch == 'x86_64':
            arch_suffix = 'linux-x64'
        elif arch == 'aarch64':
            arch_suffix = 'linux-arm64'
        else:
            raise RuntimeError(f"Unsupported architecture: {arch}")

        # Build download URL
        # Format: https://github.com/PowerShell/PowerShell/releases/download/v7.4.6/powershell-7.4.6-linux-x64.tar.gz
        filename = f"powershell-{version}-{arch_suffix}.tar.gz"
        url = f"https://github.com/PowerShell/PowerShell/releases/download/v{version}/{filename}"

        download_path = cls.CACHE_DIR / filename

        # Create a temporary extraction directory
        temp_extract_dir = cls.CACHE_DIR / f"powershell-extract-{version}"

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

            # Install to bin/powershell directory
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing PowerShell binaries")

            # Create bin/powershell directory if it doesn't exist
            if bin_dir.exists():
                import shutil
                shutil.rmtree(bin_dir)

            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy all extracted files to bin/powershell
            cls.set_status("Installing binaries")
            import shutil

            for item in temp_extract_dir.iterdir():
                dst_item = bin_dir / item.name
                if item.is_dir():
                    shutil.copytree(str(item), str(dst_item))
                else:
                    shutil.copy2(str(item), str(dst_item))
                    # Make executable files executable
                    if item.suffix == '' and not item.name.endswith('.dll'):
                        dst_item.chmod(0o755)

            # Ensure pwsh is executable
            if binary_path.exists():
                binary_path.chmod(0o755)

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            # Optionally remove download file if not using cache
            if not pulsar_env.PULSAR_CACHE_DIR and download_path.exists():
                download_path.unlink()

            cls.set_status("Complete", "green")
            cls.logger.info(f"PowerShell installed successfully to {binary_path}")

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
        """Uninstall PowerShell from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("PowerShell is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'powershell'

        try:
            import shutil
            shutil.rmtree(bin_dir)
            cls.logger.info(f"Removed {bin_dir}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise


class PowerShellWindows(WindowsPackage):
    name = 'powershell'
    description = 'Cross-platform task automation and configuration management framework'

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest PowerShell version from GitHub API"""
        try:
            url = "https://api.github.com/repos/PowerShell/PowerShell/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Remove 'v' prefix from tag_name (e.g., "v7.6.0" -> "7.6.0")
                return data['tag_name'].lstrip('v')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 7.4.6")
            return "7.4.6"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if PowerShell is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['where', 'pwsh'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if PowerShell is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'powershell' / 'pwsh.exe'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of PowerShell"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'powershell' / 'pwsh.exe'
            result = subprocess.run(
                [str(binary_path), '-Command', '$PSVersionTable.PSVersion.ToString()'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("PowerShell environment activated")

        # Add PowerShell bin subdirectory to PATH
        powershell_bin = os.path.join(pulsar_env.PULSAR_BIN_DIR, 'powershell')
        current_path = os.environ.get('PATH', '')
        if powershell_bin not in current_path:
            pulsar_env.set_env('PATH', f"{powershell_bin};{current_path}")

        # Set PowerShell config directory
        config_dir = os.path.join(pulsar_env.PULSAR_CONFIG_DIR, 'powershell')
        pulsar_env.set_env('PSModulePath', config_dir)

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install PowerShell to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'powershell'
        binary_path = bin_dir / 'pwsh.exe'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("PowerShell is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting PowerShell installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Determine architecture
        arch = pulsar_env.ARCH
        if arch == 'x86_64':
            arch_suffix = 'win-x64'
        elif arch == 'aarch64':
            arch_suffix = 'win-arm64'
        else:
            raise RuntimeError(f"Unsupported architecture: {arch}")

        # Build download URL
        # Format: https://github.com/PowerShell/PowerShell/releases/download/v7.4.6/PowerShell-7.4.6-win-x64.zip
        filename = f"PowerShell-{version}-{arch_suffix}.zip"
        url = f"https://github.com/PowerShell/PowerShell/releases/download/v{version}/{filename}"

        download_path = cls.CACHE_DIR / filename

        # Create a temporary extraction directory
        temp_extract_dir = cls.CACHE_DIR / f"powershell-extract-{version}"

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

            # Install to bin/powershell directory
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing PowerShell binaries")

            # Create bin/powershell directory if it doesn't exist
            if bin_dir.exists():
                import shutil
                shutil.rmtree(bin_dir)

            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy all extracted files to bin/powershell
            cls.set_status("Installing binaries")
            import shutil

            for item in temp_extract_dir.iterdir():
                dst_item = bin_dir / item.name
                if item.is_dir():
                    shutil.copytree(str(item), str(dst_item))
                else:
                    shutil.copy2(str(item), str(dst_item))

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            # Optionally remove download file if not using cache
            if not pulsar_env.PULSAR_CACHE_DIR and download_path.exists():
                download_path.unlink()

            cls.set_status("Complete", "green")
            cls.logger.info(f"PowerShell installed successfully to {binary_path}")

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
        """Uninstall PowerShell from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("PowerShell is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'powershell'

        try:
            import shutil
            shutil.rmtree(bin_dir)
            cls.logger.info(f"Removed {bin_dir}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
