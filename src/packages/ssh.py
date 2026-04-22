import subprocess
import re
from pathlib import Path

from package_classes import LinuxPackage, WindowsPackage
import pulsar_env


class SSHLinux(LinuxPackage):
    name = 'ssh'
    description = 'OpenSSH secure shell client'

    @classmethod
    def is_installed(cls) -> bool:
        try:
            result = subprocess.run(
                ['which', 'ssh'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        # SSH is always system-wide, never installed with Pulsar
        return False

    @classmethod
    def get_version(cls) -> str:
        if not cls.is_installed():
            return "Not installed"

        try:
            result = subprocess.run(
                ['ssh', '-V'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # SSH version goes to stderr
            output = result.stderr if result.stderr else result.stdout
            if output:
                # Extract version from output like "OpenSSH_8.9p1 Ubuntu-3ubuntu0.6, OpenSSL 3.0.2 15 Mar 2022"
                match = re.search(r'OpenSSH[_\s]+([^\s,]+)', output)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        cls.logger.info("SSH environment activated")

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
            cls.logger.info("OpenSSH client is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting OpenSSH client installation (system-wide)")

        try:
            # Detect package manager and install
            cls.set_status("Installing via system package manager", "yellow")

            # Try apt-get (Debian/Ubuntu)
            if Path('/usr/bin/apt-get').exists():
                cls.logger.info("Using apt-get to install openssh-client")
                result = subprocess.run(
                    ['sudo', 'apt-get', 'install', '-y', 'openssh-client'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise RuntimeError(f"apt-get install failed: {result.stderr}")

            # Try yum (RHEL/CentOS)
            elif Path('/usr/bin/yum').exists():
                cls.logger.info("Using yum to install openssh-clients")
                result = subprocess.run(
                    ['sudo', 'yum', 'install', '-y', 'openssh-clients'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise RuntimeError(f"yum install failed: {result.stderr}")

            # Try dnf (Fedora)
            elif Path('/usr/bin/dnf').exists():
                cls.logger.info("Using dnf to install openssh-clients")
                result = subprocess.run(
                    ['sudo', 'dnf', 'install', '-y', 'openssh-clients'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise RuntimeError(f"dnf install failed: {result.stderr}")

            # Try pacman (Arch)
            elif Path('/usr/bin/pacman').exists():
                cls.logger.info("Using pacman to install openssh")
                result = subprocess.run(
                    ['sudo', 'pacman', '-S', '--noconfirm', 'openssh'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise RuntimeError(f"pacman install failed: {result.stderr}")

            else:
                raise RuntimeError("Could not detect a supported package manager (apt-get, yum, dnf, pacman)")

            cls.set_status("Complete", "green")
            cls.logger.info("OpenSSH client installed successfully")

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            raise

    @classmethod
    def uninstall(cls):
        if not cls.is_installed():
            cls.logger.info("OpenSSH client is not installed")
            return

        cls.logger.warning("SSH was installed system-wide and cannot be uninstalled via Pulsar.")
        cls.logger.warning("Use your system package manager to uninstall it if needed.")
        cls.logger.warning("Examples:")
        cls.logger.warning("  Ubuntu/Debian: sudo apt-get remove openssh-client")
        cls.logger.warning("  RHEL/CentOS/Fedora: sudo yum remove openssh-clients")
        cls.logger.warning("  Arch: sudo pacman -R openssh")


class SSHWindows(WindowsPackage):
    name = 'ssh'
    description = 'OpenSSH secure shell client'

    @classmethod
    def is_installed(cls) -> bool:
        try:
            result = subprocess.run(
                ['where', 'ssh'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_installed_with_pulsar(cls) -> bool:
        # SSH is always system-wide, never installed with Pulsar
        return False

    @classmethod
    def get_version(cls) -> str:
        if not cls.is_installed():
            return "Not installed"

        try:
            result = subprocess.run(
                ['ssh', '-V'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # SSH version goes to stderr
            output = result.stderr if result.stderr else result.stdout
            if output:
                # Extract version from output like "OpenSSH_for_Windows_8.1p1, LibreSSL 3.0.2"
                match = re.search(r'OpenSSH[_\w]*[_\s]+([^\s,]+)', output)
                if match:
                    return match.group(1)
        except Exception as e:
            cls.logger.error(f"Failed to get version: {e}")

        return "Unknown"

    @classmethod
    def on_env_activate(cls):
        cls.logger.info("SSH environment activated")

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
            cls.logger.info("OpenSSH client is already installed")
            return

        cls.set_status("Initializing")
        cls.logger.info("Starting OpenSSH client installation (system-wide)")

        try:
            # Try to install via Windows Optional Features
            cls.set_status("Checking Windows features", "yellow")
            cls.logger.info("Checking if OpenSSH.Client feature is available")

            # Check if the feature is available
            result = subprocess.run(
                ['powershell', '-Command',
                 'Get-WindowsCapability -Online | Where-Object Name -like "OpenSSH.Client*"'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and 'OpenSSH.Client' in result.stdout:
                cls.set_status("Installing via Windows features", "yellow")
                cls.logger.info("Installing OpenSSH.Client via Windows Optional Features")

                # Install the feature
                result = subprocess.run(
                    ['powershell', '-Command',
                     'Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Failed to install OpenSSH.Client: {result.stderr}")

                cls.set_status("Complete", "green")
                cls.logger.info("OpenSSH client installed successfully via Windows Optional Features")
                return

            # If Windows features didn't work, try winget
            cls.set_status("Checking winget", "yellow")
            cls.logger.info("Windows features not available, trying winget")

            result = subprocess.run(
                ['where', 'winget'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                cls.set_status("Installing via winget", "yellow")
                cls.logger.info("Installing OpenSSH via winget")

                result = subprocess.run(
                    ['winget', 'install', '-e', '--id', 'Microsoft.OpenSSH.Beta', '--silent'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    raise RuntimeError(f"winget install failed: {result.stderr}")

                cls.set_status("Complete", "green")
                cls.logger.info("OpenSSH client installed successfully via winget")
                return

            # If neither worked, provide manual instructions
            raise RuntimeError(
                "Could not install OpenSSH automatically. Please install manually:\n"
                "1. Open Settings > Apps > Optional Features\n"
                "2. Click 'Add a feature'\n"
                "3. Search for 'OpenSSH Client' and install it\n"
                "OR use winget: winget install Microsoft.OpenSSH.Beta"
            )

        except Exception as e:
            cls.set_status("Error", "bold red")
            cls.logger.error(f"Installation failed: {e}")
            raise

    @classmethod
    def uninstall(cls):
        if not cls.is_installed():
            cls.logger.info("OpenSSH client is not installed")
            return

        cls.logger.warning("SSH was installed system-wide and cannot be uninstalled via Pulsar.")
        cls.logger.warning("Use Windows Settings or package manager to uninstall it if needed.")
        cls.logger.warning("Examples:")
        cls.logger.warning("  Settings: Settings > Apps > Optional Features > OpenSSH Client")
        cls.logger.warning("  PowerShell: Remove-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0")
        cls.logger.warning("  winget: winget uninstall Microsoft.OpenSSH.Beta")
