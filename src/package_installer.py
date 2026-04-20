import time
import random
# from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
import threading
import typing

from rich.console import Console
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
from rich.text import Text
from rich.table import Table

import pulsar_env
from package_classes import _PulsarPackage, LinuxPackage, WindowsPackage, LastLogHandler

console = Console()


class PackageInstaller:

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.packages: dict[str, _PulsarPackage] = dict()
        self.package_versions: dict[str, str | None] = dict()
        self.thread_lock = threading.Lock()

    def install_packages(
            self,
            package_strs: list[str],
            reinstall: bool = False,
            refresh_cache: bool = False
    ):

        package_list = LinuxPackage.PACKAGE_LIST \
            if pulsar_env.OS == 'linux' \
            else WindowsPackage.PACKAGE_LIST

        packages_to_install = {}
        packages_to_skip = []

        for pkg_str in package_strs:

            if '==' in pkg_str:
                split = pkg_str.split('==', 1)
                name = split[0]
                version = split[1]
            else:
                name = pkg_str
                version = None

            if name not in package_list:
                raise ValueError(f"'{name}' for {pulsar_env.OS} is not found.")

            pkg = package_list[name]

            # Check if package is already installed
            if not reinstall and pkg.is_installed_with_pulsar():
                current_version = pkg.get_version()

                # If a specific version is requested, check if it matches
                if version is not None:
                    if current_version == version:
                        # Version matches, skip installation
                        pkg.set_status("Already installed", "green")
                        pkg.logger.info(f"Version {version} already installed, skipping")
                        packages_to_skip.append(name)
                        self.packages[name] = pkg
                        continue
                    else:
                        # Version mismatch, uninstall and reinstall
                        pkg.set_status("Uninstalling old version", "yellow")
                        pkg.logger.info(f"Version mismatch: {current_version} != {version}, reinstalling")
                        try:
                            pkg.uninstall()
                        except Exception as e:
                            pkg.logger.error(f"Failed to uninstall: {e}")
                            raise
                else:
                    # No version specified, skip installation
                    pkg.set_status("Already installed", "green")
                    pkg.logger.info(f"Already installed (version {current_version}), skipping")
                    packages_to_skip.append(name)
                    self.packages[name] = pkg
                    continue

            # Package needs to be installed
            pkg.set_status("Pending")
            packages_to_install[name] = pkg
            self.package_versions[name] = version

        # Add skipped packages to self.packages for display
        self.packages.update(packages_to_install)

        # If all packages are skipped, just display and return
        if not packages_to_install:
            console.print("[dim]All packages are already installed[/dim]")
            return

        with Live(self.create_display(), refresh_per_second=10, console=Console()) as live:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        pkg.install,
                        self.package_versions[pkg.name],
                        reinstall,
                        refresh_cache,
                    ): pkg

                    for pkg in packages_to_install.values()
                }

                # Update display continuously while tasks run
                while futures:
                    done, _ = concurrent.futures.wait(
                        futures.keys(),
                        timeout=0.1,
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    for future in done:
                        pkg = futures.pop(future)
                        try:
                            future.result()
                        except Exception as e:
                            pkg.set_status("Error", "bold red")
                            pkg.logger.error(str(e))

                    live.update(self.create_display())

        console.print("Finished")

    def create_display(self) -> Table:
        table = Table(show_header=False, show_edge=False, pad_edge=False, box=None)
        table.add_column("Package", width=20)
        table.add_column("Status", width=15)
        table.add_column("Progress")

        for name, pkg in self.packages.items():
            pkg_text = Text(f"📦 {name}", style='bold blue')
            status_text = Text(pkg.status, style=pkg.status_style)

            if pkg.download_progress is not None:
                progress_display = pkg.download_progress
            else:
                # Get the last log message
                last_log = ""
                for handler in pkg.logger.handlers:
                    if isinstance(handler, LastLogHandler) and handler.last_record:
                        last_log = handler.last_record.getMessage()
                        break
                progress_display = Text(last_log, style='dim')

            table.add_row(pkg_text, status_text, progress_display)

        return table
