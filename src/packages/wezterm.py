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





class WeztermLinux(LinuxPackage):
    name = 'wezterm'
    description = 'GPU-accelerated terminal emulator'

    @staticmethod
    def detect_linux_distro():
        """
        Detect Linux distribution and version from /etc/os-release.
        Returns tuple of (distro_name, version_id) or None if cannot detect.
        """
        try:
            os_release_path = Path('/etc/os-release')
            if not os_release_path.exists():
                return None

            distro_info = {}
            with open(os_release_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes
                        value = value.strip('"').strip("'")
                        distro_info[key] = value

            distro_id = distro_info.get('ID', '').lower()
            version_id = distro_info.get('VERSION_ID', '')

            return (distro_id, version_id)
        except Exception:
            return None

    @staticmethod
    def get_wezterm_distro_suffix():
        """
        Get the appropriate wezterm distro suffix based on detected distro.
        Returns tuple of (suffix, is_appimage) or uses AppImage as fallback.

        Examples:
            Ubuntu 22.04 -> ('Ubuntu22.04', False)
            Debian 12 -> ('Debian12', False)
            Unknown -> ('Ubuntu20.04', True)  # AppImage fallback
        """
        distro_info = WeztermLinux.detect_linux_distro()

        if not distro_info:
            # Fallback to AppImage for unknown distros
            return ('Ubuntu20.04', True)

        distro_id, version_id = distro_info

        # Map distro to wezterm naming
        if distro_id == 'ubuntu':
            # Map Ubuntu versions to available wezterm builds
            if version_id.startswith('24'):
                return ('Ubuntu22.04', False)  # Use 22.04 for 24.x
            elif version_id.startswith('22'):
                return ('Ubuntu22.04', False)
            elif version_id.startswith('20'):
                return ('Ubuntu20.04', False)
            else:
                return ('Ubuntu20.04', False)  # Older versions use 20.04

        elif distro_id == 'debian':
            # Map Debian versions
            if version_id.startswith('12') or int(version_id.split('.')[0]) >= 12:
                return ('Debian12', False)
            elif version_id.startswith('11'):
                return ('Debian11', False)
            elif version_id.startswith('10'):
                return ('Debian10', False)
            else:
                return ('Debian10', False)  # Older versions

        elif distro_id == 'fedora':
            # Fedora builds available - use generic Fedora name
            # Note: wezterm uses format like "Fedora39" but we'll need to check what's available
            return (f'Fedora{version_id}', False)

        elif distro_id in ['centos', 'rhel', 'rocky', 'almalinux']:
            # RHEL-based distros - try Fedora builds
            major_version = version_id.split('.')[0]
            return (f'Fedora{major_version}', False)

        elif distro_id in ['arch', 'manjaro', 'endeavouros']:
            # Arch-based distros - use AppImage for maximum compatibility
            return ('Ubuntu20.04', True)

        else:
            raise OSError(f"Distribution not supported: {distro_id}")

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest wezterm version from GitHub API"""
        try:
            url = "https://api.github.com/repos/wez/wezterm/releases/latest"
            request = urllib.request.Request(url)
            # GitHub API may redirect, so we need to handle that
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Wezterm uses date-based tags without 'v' prefix (e.g., "20240203-110809-5046fc22")
                return data['tag_name']
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 20230712-072601-f4abf8fd")
            return "20230712-072601-f4abf8fd"

    @classmethod
    def is_installed(cls) -> bool:
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
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm' / 'wezterm'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm' / 'wezterm'
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
        cls.logger.info("Wezterm environment activated")

        # Add wezterm bin subdirectory to PATH
        wezterm_bin = os.path.join(pulsar_env.PULSAR_BIN_DIR, 'wezterm')
        pulsar_env.add_to_path(wezterm_bin)

        # Set WEZTERM_CONFIG_FILE to point to Pulsar's config directory
        config_file = os.path.join(pulsar_env.PULSAR_CONFIG_DIR, 'wezterm', 'wezterm.lua')
        pulsar_env.set_env('WEZTERM_CONFIG_FILE', config_file)

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm'
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
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Detect distro and get appropriate build
        distro_suffix, is_appimage = cls.get_wezterm_distro_suffix()
        cls.logger.info(f"Detected distro suffix: {distro_suffix}, AppImage: {is_appimage}")

        # Build download URL based on format
        if is_appimage:
            # AppImage format: WezTerm-{version}-Ubuntu20.04.AppImage
            filename = f"WezTerm-{version}-{distro_suffix}.AppImage"
        else:
            # Tar.xz format: wezterm-{version}.Ubuntu22.04.tar.xz
            # For ARM64, format is: wezterm-{version}.Ubuntu22.04.arm64.deb (but we use tar.xz)
            filename = f"wezterm-{version}.{distro_suffix}.tar.xz"

        url = f"https://github.com/wez/wezterm/releases/download/{version}/{filename}"
        cls.logger.info(f"Download URL: {url}")

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

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            import shutil

            if is_appimage:
                # AppImage doesn't need extraction - just copy and make executable
                cls.set_status("Installing", "cyan")
                cls.logger.info("Installing AppImage")

                cls.logger.info(f"Copying AppImage to {binary_path}")
                shutil.copy2(str(download_path), str(binary_path))
                # Make AppImage executable
                binary_path.chmod(0o755)
                cls.logger.info("AppImage installed and made executable")

            else:
                # Extract tar.xz file
                cls.set_status("Extracting", "cyan")
                cls.logger.info(f"Extracting archive")

                # Clean temp directory if it exists
                if temp_extract_dir.exists():
                    shutil.rmtree(temp_extract_dir)

                temp_extract_dir.mkdir(parents=True, exist_ok=True)

                # Extract tar.xz file
                with tarfile.open(download_path, 'r:xz') as tar:
                    tar.extractall(temp_extract_dir)

                # Find the wezterm binaries directory in the extracted files
                cls.set_status("Installing", "cyan")
                cls.logger.info("Finding wezterm binaries")

                wezterm_bin_dir = None
                for potential_dir in temp_extract_dir.rglob("bin"):
                    # Look for the usr/bin directory containing wezterm binaries
                    if potential_dir.is_dir() and (potential_dir / "wezterm").exists():
                        wezterm_bin_dir = potential_dir
                        break

                if not wezterm_bin_dir:
                    raise RuntimeError("Could not find wezterm binaries in archive")

                cls.logger.info(f"Found binaries at {wezterm_bin_dir}")

                # Copy all wezterm-related binaries
                cls.set_status("Installing binaries")

                wezterm_binaries = [
                    "wezterm",
                    "wezterm-gui",
                    "wezterm-mux-server",
                    "open-wezterm-here",
                    "strip-ansi-escapes"
                ]

                for binary_name in wezterm_binaries:
                    src_binary = wezterm_bin_dir / binary_name
                    if src_binary.exists():
                        dst_binary = bin_dir / binary_name
                        cls.logger.info(f"Installing {binary_name} to {dst_binary}")
                        shutil.copy2(str(src_binary), str(dst_binary))
                        # Make binary executable
                        dst_binary.chmod(0o755)

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
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Wezterm is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm'

        try:
            # Remove the entire wezterm directory
            if bin_dir.exists():
                import shutil
                shutil.rmtree(bin_dir)
                cls.logger.info(f"Removed {bin_dir}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise


class WeztermWindows(WindowsPackage):
    name = 'wezterm'
    description = 'GPU-accelerated terminal emulator'

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest wezterm version from GitHub API"""
        try:
            url = "https://api.github.com/repos/wez/wezterm/releases/latest"
            request = urllib.request.Request(url)
            # GitHub API may redirect, so we need to handle that
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Wezterm uses date-based tags without 'v' prefix (e.g., "20240203-110809-5046fc22")
                return data['tag_name']
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 20230712-072601-f4abf8fd")
            return "20230712-072601-f4abf8fd"

    @classmethod
    def is_installed(cls) -> bool:
        try:
            result = subprocess.run(
                ['where', 'wezterm'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm' / 'wezterm.exe'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm' / 'wezterm.exe'
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
        cls.logger.info("Wezterm environment activated")

        # Add wezterm bin subdirectory to PATH
        wezterm_bin = os.path.join(pulsar_env.PULSAR_BIN_DIR, 'wezterm')
        pulsar_env.add_to_path(wezterm_bin)

        # Set WEZTERM_CONFIG_FILE to point to Pulsar's config directory
        config_file = os.path.join(pulsar_env.PULSAR_CONFIG_DIR, 'wezterm', 'wezterm.lua')
        pulsar_env.set_env('WEZTERM_CONFIG_FILE', config_file)

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm'
        binary_path = bin_dir / 'wezterm.exe'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Wezterm is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Wezterm installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL
        # Format: https://github.com/wez/wezterm/releases/download/20230712-072601-f4abf8fd/WezTerm-windows-20230712-072601-f4abf8fd.zip
        filename = f"WezTerm-windows-{version}.zip"
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

            # Extract zip file
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)

            # Find the wezterm binaries directory in the extracted files
            cls.set_status("Installing", "cyan")
            cls.logger.info("Finding wezterm binaries")

            # The zip typically extracts to a directory like WezTerm-windows-{version}/
            wezterm_bin_dir = None
            for potential_dir in temp_extract_dir.rglob("*"):
                # Look for directory containing wezterm.exe
                if potential_dir.is_dir() and (potential_dir / "wezterm.exe").exists():
                    wezterm_bin_dir = potential_dir
                    break

            if not wezterm_bin_dir:
                raise RuntimeError("Could not find wezterm binaries in archive")

            cls.logger.info(f"Found binaries at {wezterm_bin_dir}")

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy all wezterm-related binaries
            cls.set_status("Installing binaries")
            import shutil

            wezterm_binaries = [
                "wezterm.exe",
                "wezterm-gui.exe",
                "wezterm-mux-server.exe",
                "strip-ansi-escapes.exe"
            ]

            for binary_name in wezterm_binaries:
                src_binary = wezterm_bin_dir / binary_name
                if src_binary.exists():
                    dst_binary = bin_dir / binary_name
                    cls.logger.info(f"Installing {binary_name} to {dst_binary}")
                    shutil.copy2(str(src_binary), str(dst_binary))

            # Copy DLL files if they exist
            for dll_file in wezterm_bin_dir.glob("*.dll"):
                dst_dll = bin_dir / dll_file.name
                cls.logger.info(f"Installing {dll_file.name} to {dst_dll}")
                shutil.copy2(str(dll_file), str(dst_dll))

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
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Wezterm is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm'

        try:
            # Remove the entire wezterm directory
            if bin_dir.exists():
                import shutil
                shutil.rmtree(bin_dir)
                cls.logger.info(f"Removed {bin_dir}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
