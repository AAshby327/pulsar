import subprocess
import tarfile
import zipfile
import re
import json
import urllib.request
import shutil
from pathlib import Path

from package_classes import LinuxPackage, WindowsPackage
import pulsar_env


class ClangLinux(LinuxPackage):
    name = 'clang'
    description = 'C language family frontend for LLVM'
    dependencies = []

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest LLVM/Clang version from GitHub API"""
        try:
            url = "https://api.github.com/repos/llvm/llvm-project/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Version format includes 'llvmorg-' prefix (e.g., "llvmorg-19.1.7")
                tag = data['tag_name']
                # Remove 'llvmorg-' prefix
                return tag.replace('llvmorg-', '')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 19.1.7")
            return "19.1.7"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if clang is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['which', 'clang'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if clang is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'llvm' / 'bin' / 'clang'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of clang"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'llvm' / 'bin' / 'clang'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "clang version 19.1.7"
                match = re.search(r'clang version\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("Clang environment activated")

        # Add llvm bin subdirectory to PATH
        llvm_bin = Path(pulsar_env.PULSAR_BIN_DIR) / 'llvm' / 'bin'
        if llvm_bin.exists():
            pulsar_env.add_to_path(str(llvm_bin))
            cls.logger.info(f"Added {llvm_bin} to PATH")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install LLVM/Clang to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        llvm_dir = bin_dir / 'llvm'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Clang is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Clang installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.4/LLVM-22.1.4-Linux-X64.tar.xz
        if pulsar_env.ARCH == 'x86_64':
            arch_suffix = 'X64'
        elif pulsar_env.ARCH == 'aarch64':
            arch_suffix = 'ARM64'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"LLVM-{version}-Linux-{arch_suffix}.tar.xz"
        url = f"https://github.com/llvm/llvm-project/releases/download/llvmorg-{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"llvm-extract-{version}"

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
                cls.logger.info(f"Downloading LLVM/Clang from GitHub releases (this may take a while, ~500MB)")

                # Ensure cache directory exists
                cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

                cls.download(url, download_path)

            # Extract to temporary directory
            cls.set_status("Extracting", "cyan")
            cls.logger.info(f"Extracting archive")

            # Clean temp directory if it exists
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)

            temp_extract_dir.mkdir(parents=True, exist_ok=True)

            # Extract tar.xz file
            # Use streaming extraction to avoid seeking issues on Windows
            try:
                with tarfile.open(download_path, 'r:xz') as tar:
                    # Extract members one by one to avoid seeking
                    for member in tar:
                        tar.extract(member, temp_extract_dir)
            except Exception as e:
                cls.logger.error(f"Standard extraction failed: {e}")
                # Try alternative: decompress xz first, then extract tar
                cls.logger.info("Attempting two-stage extraction (xz -> tar)")
                import lzma

                temp_tar = cls.CACHE_DIR / f"llvm-{version}.tar"

                # Decompress xz to tar
                with lzma.open(download_path, 'rb') as xz_file:
                    with open(temp_tar, 'wb') as tar_file:
                        shutil.copyfileobj(xz_file, tar_file, length=1024*1024)

                # Extract tar
                with tarfile.open(temp_tar, 'r:') as tar:
                    tar.extractall(temp_extract_dir)

                # Clean up temp tar
                temp_tar.unlink()

            # Install LLVM
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing LLVM/Clang")

            # Find the extracted directory (structure may vary by version)
            extracted_dirs = [d for d in temp_extract_dir.iterdir() if d.is_dir()]
            if len(extracted_dirs) != 1:
                raise RuntimeError(f"Expected exactly one directory in {temp_extract_dir}, found {len(extracted_dirs)}")
            extracted_dir = extracted_dirs[0]
            cls.logger.info(f"Found extracted directory: {extracted_dir.name}")

            # Remove old installation if it exists
            if llvm_dir.exists():
                cls.logger.info("Removing old LLVM installation")
                shutil.rmtree(llvm_dir)

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy extracted directory to bin/llvm (more reliable than move on Windows)
            cls.logger.info(f"Installing LLVM to {llvm_dir}")
            shutil.copytree(
                str(extracted_dir),
                str(llvm_dir),
                symlinks=False,  # Copy symlink targets instead of symlinks (Windows compatible)
                ignore_dangling_symlinks=True  # Skip broken symlinks
            )

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"Clang installed successfully to {llvm_dir}")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            # Cleanup on error
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            raise

    @classmethod
    def uninstall(cls):
        """Uninstall Clang from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Clang is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        llvm_dir = bin_dir / 'llvm'

        try:
            if llvm_dir.exists():
                shutil.rmtree(llvm_dir)
                cls.logger.info(f"Removed {llvm_dir}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise


class ClangWindows(WindowsPackage):
    name = 'clang'
    description = 'C language family frontend for LLVM'
    dependencies = []

    @classmethod
    def get_latest_version(cls) -> str:
        """Fetch the latest LLVM/Clang version from GitHub API"""
        try:
            url = "https://api.github.com/repos/llvm/llvm-project/releases/latest"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                # Version format includes 'llvmorg-' prefix (e.g., "llvmorg-19.1.7")
                tag = data['tag_name']
                # Remove 'llvmorg-' prefix
                return tag.replace('llvmorg-', '')
        except Exception as e:
            cls.logger.warning(f"Failed to fetch latest version: {e}, falling back to 19.1.7")
            return "19.1.7"

    @classmethod
    def is_installed(cls) -> bool:
        """Check if clang is installed anywhere on the system"""
        try:
            result = subprocess.run(
                ['where', 'clang'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        """Check if clang is installed in Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            return False
        binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'llvm' / 'bin' / 'clang.exe'
        return binary_path.exists() and binary_path.is_file()

    @classmethod
    def get_version(cls) -> str:
        """Get the installed version of clang"""
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'llvm' / 'bin' / 'clang.exe'
            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "clang version 19.1.7"
                match = re.search(r'clang version\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        """Called when the pulsar environment is activated"""
        cls.logger.info("Clang environment activated")

        # Add llvm bin subdirectory to PATH
        llvm_bin = Path(pulsar_env.PULSAR_BIN_DIR) / 'llvm' / 'bin'
        if llvm_bin.exists():
            pulsar_env.add_to_path(str(llvm_bin))
            cls.logger.info(f"Added {llvm_bin} to PATH")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        """Install LLVM/Clang to the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        llvm_dir = bin_dir / 'llvm'

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Clang is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Clang installation")

        # Determine version to install
        if version is None:
            cls.logger.info("Fetching latest version from GitHub...")
            version = cls.get_latest_version()

        cls.logger.info(f"Installing version: {version}")

        # Build download URL based on architecture
        # Format: https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-win64.exe
        # We'll use the 7z archive instead for easier extraction
        # Format: https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/LLVM-19.1.7-win64.7z (not available)
        # Actually, let's use the tar.xz format which is available
        # Format: https://github.com/llvm/llvm-project/releases/download/llvmorg-19.1.7/clang+llvm-19.1.7-x86_64-pc-windows-msvc.tar.xz

        if pulsar_env.ARCH == 'x86_64':
            arch_target = 'x86_64-pc-windows-msvc'
        elif pulsar_env.ARCH == 'aarch64':
            arch_target = 'aarch64-pc-windows-msvc'
        else:
            raise RuntimeError(f"Unsupported architecture: {pulsar_env.ARCH}")

        filename = f"clang+llvm-{version}-{arch_target}.tar.xz"
        url = f"https://github.com/llvm/llvm-project/releases/download/llvmorg-{version}/{filename}"

        download_path = cls.CACHE_DIR / filename
        temp_extract_dir = cls.CACHE_DIR / f"llvm-extract-{version}"

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
                cls.logger.info(f"Downloading LLVM/Clang from GitHub releases (this may take a while, ~500MB)")

                # Ensure cache directory exists
                cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

                cls.download(url, download_path)

            # Extract to temporary directory
            cls.set_status("Extracting", "cyan")
            cls.logger.info(f"Extracting archive")

            # Clean temp directory if it exists
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)

            temp_extract_dir.mkdir(parents=True, exist_ok=True)

            # Extract tar.xz file
            # Use streaming extraction to avoid seeking issues on Windows
            try:
                with tarfile.open(download_path, 'r:xz') as tar:
                    # Extract members one by one to avoid seeking
                    for member in tar:
                        tar.extract(member, temp_extract_dir)
            except Exception as e:
                cls.logger.error(f"Standard extraction failed: {e}")
                # Try alternative: decompress xz first, then extract tar
                cls.logger.info("Attempting two-stage extraction (xz -> tar)")
                import lzma

                temp_tar = cls.CACHE_DIR / f"llvm-{version}.tar"

                # Decompress xz to tar
                with lzma.open(download_path, 'rb') as xz_file:
                    with open(temp_tar, 'wb') as tar_file:
                        shutil.copyfileobj(xz_file, tar_file, length=1024*1024)

                # Extract tar
                with tarfile.open(temp_tar, 'r:') as tar:
                    tar.extractall(temp_extract_dir)

                # Clean up temp tar
                temp_tar.unlink()

            # Install LLVM
            cls.set_status("Installing", "cyan")
            cls.logger.info("Installing LLVM/Clang")

            # Find the extracted directory (structure may vary by version)
            extracted_dirs = [d for d in temp_extract_dir.iterdir() if d.is_dir()]
            if len(extracted_dirs) != 1:
                raise RuntimeError(f"Expected exactly one directory in {temp_extract_dir}, found {len(extracted_dirs)}")
            extracted_dir = extracted_dirs[0]
            cls.logger.info(f"Found extracted directory: {extracted_dir.name}")

            # Remove old installation if it exists
            if llvm_dir.exists():
                cls.logger.info("Removing old LLVM installation")
                shutil.rmtree(llvm_dir)

            # Create bin directory if it doesn't exist
            bin_dir.mkdir(parents=True, exist_ok=True)

            # Copy extracted directory to bin/llvm (more reliable than move on Windows)
            cls.logger.info(f"Installing LLVM to {llvm_dir}")
            shutil.copytree(
                str(extracted_dir),
                str(llvm_dir),
                symlinks=False,  # Copy symlink targets instead of symlinks (Windows compatible)
                ignore_dangling_symlinks=True  # Skip broken symlinks
            )

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)

            cls.set_status("Complete", "green")
            cls.logger.info(f"Clang installed successfully to {llvm_dir}")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            # Cleanup on error
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            raise

    @classmethod
    def uninstall(cls):
        """Uninstall Clang from the Pulsar bin directory"""
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Clang is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        llvm_dir = bin_dir / 'llvm'

        try:
            if llvm_dir.exists():
                shutil.rmtree(llvm_dir)
                cls.logger.info(f"Removed {llvm_dir}")
        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
