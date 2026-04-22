import os
import subprocess
import zipfile
import re
from pathlib import Path

from package_classes import LinuxPackage, WindowsPackage
import pulsar_env


class GitLinux(LinuxPackage):
    name = 'git'
    description = 'Distributed version control system'

    @classmethod
    def is_installed(cls) -> bool:
        try:
            result = subprocess.run(
                ['which', 'git'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        return False

    @classmethod
    def get_version(cls) -> str:
        if not cls.is_installed():
            return "Not installed"

        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "git version 2.34.1"
                match = re.search(r'git version\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        cls.logger.info("Git environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        # Check if already installed
        if cls.is_installed() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Git is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Git installation (system-wide)")

        try:
            # Detect package manager and install
            cls.set_status("Installing via system package manager", "yellow")

            # Try apt-get (Debian/Ubuntu)
            if Path('/usr/bin/apt-get').exists():
                cls.logger.info("Using apt-get to install git")
                result = subprocess.run(
                    ['sudo', 'apt-get', 'install', '-y', 'git'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise RuntimeError(f"apt-get install failed: {result.stderr}")

            # Try yum (RHEL/CentOS/Fedora)
            elif Path('/usr/bin/yum').exists():
                cls.logger.info("Using yum to install git")
                result = subprocess.run(
                    ['sudo', 'yum', 'install', '-y', 'git'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise RuntimeError(f"yum install failed: {result.stderr}")

            # Try dnf (Fedora)
            elif Path('/usr/bin/dnf').exists():
                cls.logger.info("Using dnf to install git")
                result = subprocess.run(
                    ['sudo', 'dnf', 'install', '-y', 'git'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise RuntimeError(f"dnf install failed: {result.stderr}")

            # Try pacman (Arch)
            elif Path('/usr/bin/pacman').exists():
                cls.logger.info("Using pacman to install git")
                result = subprocess.run(
                    ['sudo', 'pacman', '-S', '--noconfirm', 'git'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise RuntimeError(f"pacman install failed: {result.stderr}")

            else:
                raise RuntimeError("Could not detect a supported package manager (apt-get, yum, dnf, pacman)")

            cls.set_status("Complete", "green")
            cls.logger.info("Git installed successfully")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            raise

    @classmethod
    def uninstall(cls):
        if not cls.is_installed():
            cls.logger.info("Git is not installed")
            return

        cls.logger.warning("Git was installed system-wide. Use your system package manager to uninstall it.")
        cls.logger.warning("Example: sudo apt-get remove git")


class GitWindows(WindowsPackage):
    name = 'git'
    description = 'Distributed version control system'

    @classmethod
    def is_installed(cls) -> bool:
        try:
            result = subprocess.run(
                ['where', 'git'],
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
        # Check for either git.bat or git.cmd
        bat_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'git.bat'
        cmd_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'git.cmd'
        return (bat_path.exists() and bat_path.is_file()) or (cmd_path.exists() and cmd_path.is_file())

    @classmethod
    def get_version(cls) -> str:
        if not cls.is_installed_with_pulsar():
            return "Not installed"

        try:
            # Try git.bat first, then git.cmd
            binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'git.bat'
            if not binary_path.exists():
                binary_path = Path(pulsar_env.PULSAR_BIN_DIR) / 'git.cmd'

            result = subprocess.run(
                [str(binary_path), '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from output like "git version 2.43.0.windows.1"
                match = re.search(r'git version\s+(\S+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        cls.logger.info("Git environment activated")

    @classmethod
    def install(
            cls,
            version: str | None = None,
            reinstall: bool = False,
            refresh_cache: bool = False
    ):
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)

        # Check if already installed
        if cls.is_installed_with_pulsar() and not reinstall:
            cls.set_status("Already installed", "green")
            cls.logger.info("Git is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting Git installation")

        # Determine version to install
        if version is None:
            version = "2.43.0"  # Latest stable version

        cls.logger.info(f"Installing version: {version}")

        # Build download URL for PortableGit
        # Format: https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/PortableGit-2.43.0-64-bit.7z.exe
        windows_version = f"{version}.windows.1"
        filename = f"PortableGit-{version}-64-bit.7z.exe"
        url = f"https://github.com/git-for-windows/git/releases/download/v{windows_version}/{filename}"

        download_path = cls.CACHE_DIR / filename

        # Create a temporary extraction directory
        temp_extract_dir = cls.CACHE_DIR / f"git-extract-{version}"
        git_install_dir = bin_dir / 'git'

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

            # Extract to git directory (PortableGit .7z.exe is self-extracting)
            cls.set_status("Preparing extraction", "cyan")
            cls.logger.info("Preparing to extract archive")

            # Clean directories if they exist
            import shutil
            if temp_extract_dir.exists():
                cls.logger.info("Removing old temporary directory")
                shutil.rmtree(temp_extract_dir)
            if git_install_dir.exists():
                cls.logger.info("Removing old git installation")
                shutil.rmtree(git_install_dir)

            temp_extract_dir.mkdir(parents=True, exist_ok=True)
            git_install_dir.mkdir(parents=True, exist_ok=True)

            # PortableGit is a self-extracting 7z archive
            # Run it silently without showing any windows
            cls.set_status("Extracting archive", "cyan")
            cls.logger.info("Running self-extracting archive (this may take a minute)")

            # Create startupinfo to hide the window
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creation_flags = subprocess.CREATE_NO_WINDOW
            else:
                startupinfo = None
                creation_flags = 0

            result = subprocess.run(
                [str(download_path), '-o' + str(temp_extract_dir), '-y'],
                capture_output=True,
                text=True,
                timeout=300,
                startupinfo=startupinfo,
                creationflags=creation_flags
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to extract PortableGit: {result.stderr}")

            cls.logger.info("Archive extracted successfully")

            # Move extracted files to git_install_dir
            cls.set_status("Installing files", "cyan")
            cls.logger.info("Moving extracted files to installation directory")

            file_count = 0
            for item in temp_extract_dir.iterdir():
                dest = git_install_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
                file_count += 1

            cls.logger.info(f"Installed {file_count} items")

            # Create symlink or wrapper in bin directory for git.exe
            cls.set_status("Creating wrappers", "cyan")
            cls.logger.info("Locating git.exe in installation")

            git_exe = git_install_dir / 'bin' / 'git.exe'
            if not git_exe.exists():
                git_exe = git_install_dir / 'cmd' / 'git.exe'

            if not git_exe.exists():
                raise RuntimeError("Could not find git.exe in extracted files")

            cls.logger.info(f"Found git.exe at {git_exe}")

            # Create a batch wrapper (use .bat extension)
            wrapper_path = bin_dir / 'git.bat'
            wrapper_content = f'@echo off\n"{git_exe}" %*\n'
            wrapper_path.write_text(wrapper_content)
            cls.logger.info(f"Created git.bat wrapper")

            # Also create git.cmd for compatibility
            cmd_path = bin_dir / 'git.cmd'
            cmd_path.write_text(wrapper_content)
            cls.logger.info(f"Created git.cmd wrapper")

            # Cleanup temporary extraction directory
            cls.set_status("Cleaning up", "cyan")
            cls.logger.info("Removing temporary files")
            shutil.rmtree(temp_extract_dir)
            cls.logger.info("Cleanup complete")

            cls.set_status("Complete", "green")
            cls.logger.info(f"Git installed successfully to {git_install_dir}")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            # Cleanup on error
            import shutil
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
            if git_install_dir.exists():
                shutil.rmtree(git_install_dir, ignore_errors=True)
            raise

    @classmethod
    def uninstall(cls):
        if not pulsar_env.PULSAR_BIN_DIR:
            raise RuntimeError("PULSAR_BIN_DIR is not set")

        if not cls.is_installed_with_pulsar():
            cls.logger.info("Git is not installed with Pulsar")
            return

        bin_dir = Path(pulsar_env.PULSAR_BIN_DIR)
        bat_path = bin_dir / 'git.bat'
        cmd_path = bin_dir / 'git.cmd'
        exe_path = bin_dir / 'git.exe'  # Remove old .exe if it exists
        git_install_dir = bin_dir / 'git'

        try:
            import shutil

            # Remove wrappers
            for path in [bat_path, cmd_path, exe_path]:
                if path.exists():
                    path.unlink()
                    cls.logger.info(f"Removed {path}")

            # Remove git installation directory
            if git_install_dir.exists():
                shutil.rmtree(git_install_dir)
                cls.logger.info(f"Removed {git_install_dir}")

        except Exception as e:
            cls.logger.error(f"Failed to uninstall: {e}")
            raise
