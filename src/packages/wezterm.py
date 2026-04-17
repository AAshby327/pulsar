import os
import subprocess
import tarfile
import re
from pathlib import Path

from package_classes import LinuxPackage, WindowsPackage
import pulsar_env


class WeztermLinux(LinuxPackage):
    name = 'wezterm'
    description = 'GPU-accelerated terminal emulator'

    @classmethod
    def is_installed(cls) -> bool:
        """Check if wezterm is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['which', 'wezterm'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if wezterm is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of wezterm"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "wezterm 20230712-072601-f4abf8fd"
                match = re.search(r'wezterm\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("Wezterm environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install wezterm standalone binary to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        binary_path = bin_dir / 'wezterm'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Wezterm is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Wezterm installation")

        # Determine version to install
        if version is None:
            version = "20230712-072601-f4abf8fd"  # Latest stable version

        cls.logger.info(f"Installing version: {version}")

        # Build download URL
        # Format: https://github.com/wez/wezterm/releases/download/20230712-072601-f4abf8fd/wezterm-20230712-072601-f4abf8fd.Ubuntu22.04.tar.xz
        filename = f"wezterm-{version}.Ubuntu22.04.tar.xz"
        url = f"https://github.com/wez/wezterm/releases/download/{version}/{filename}"

        download_path = cls.CACHE_DIR / filename

        # Create a temporary extraction directory
        temp_extract_dir = cls.CACHE_DIR / f"wezterm-extract-{version}"

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

            # Extract tar.xz file
            with tarfile.open(download_path, 'r:xz') as tar:
                tar.extractall(temp_extract_dir)

            # Find the wezterm binary in the extracted files
            cls.set_status("Installing", "cyan")
            cls.logger.info("Finding wezterm binary")

            wezterm_binary = None
            for potential_binary in temp_extract_dir.rglob("wezterm"):
                # Look for the main binary (not wezterm-gui, wezterm-mux-server, etc.)
                if potential_binary.is_file() and potential_binary.name == "wezterm":
                    # Check it's executable or in a bin directory
                    if "bin" in str(potential_binary.parent) or potential_binary.stat().st_mode & 0o111:
                        wezterm_binary = potential_binary
                        break

            if not wezterm_binary:
                raise RuntimeError("Could not find wezterm binary in archive")

            cls.logger.info(f"Found binary at {wezterm_binary}")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy the binary to bin/wezterm
            cls.set_status("Installing binary")
            cls.logger.info(f"Installing to {binary_path}")

            import shutil
            shutil.copy2(str(wezterm_binary), str(binary_path))

            # Make binary executable
            binary_path.chmod(0o755)

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            # Optionally remove download file if not using cache
            if not pulsar_env.PULSAR_CACHE_DIR and download_path.exists():
                download_path.unlink()

            cls.set_status("Complete", "green")
            cls.logger.info(f"Wezterm installed successfully to {binary_path}")

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
        """Uninstall wezterm from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm'

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Wezterm is not installed with Pulsar")
            return

        try:
            binary_path.unlink()
            cls.logger.info(f"Removed {binary_path}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
