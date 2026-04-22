from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.live import Live
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

    def collect_dependencies(
            self,
            pkg: _PulsarPackage,
            collected: dict[str, _PulsarPackage],
            package_list: dict[str, _PulsarPackage]
    ):
        """Recursively collect all dependencies for a package"""
        # Add this package if not already collected
        if pkg.name not in collected:
            collected[pkg.name] = pkg

            # Recursively collect dependencies
            if hasattr(pkg, 'dependencies') and pkg.dependencies:
                for dep_class in pkg.dependencies:
                    # Dependencies are class references
                    dep_name = dep_class.name
                    if dep_name in package_list:
                        dep_pkg = package_list[dep_name]
                        self.collect_dependencies(dep_pkg, collected, package_list)
                    else:
                        console.print(f"[yellow]Warning: Dependency '{dep_name}' not found in package list[/yellow]")

    def topological_sort(self, packages: dict[str, _PulsarPackage]) -> list[_PulsarPackage]:
        """Sort packages by dependencies (dependencies first)"""
        sorted_packages = []
        visited = set()
        visiting = set()

        def visit(pkg: _PulsarPackage):
            if pkg.name in visited:
                return
            if pkg.name in visiting:
                raise ValueError(f"Circular dependency detected involving package '{pkg.name}'")

            visiting.add(pkg.name)

            # Visit dependencies first
            if hasattr(pkg, 'dependencies') and pkg.dependencies:
                for dep_class in pkg.dependencies:
                    # Dependencies are class references
                    dep_name = dep_class.name
                    if dep_name in packages:
                        visit(packages[dep_name])

            visiting.remove(pkg.name)
            visited.add(pkg.name)
            sorted_packages.append(pkg)

        for pkg in packages.values():
            visit(pkg)

        return sorted_packages

    def install_packages(
            self,
            package_strs: list[str],
            reinstall: bool = False,
            refresh_cache: bool = False
    ):

        package_list = LinuxPackage.PACKAGE_LIST \
            if pulsar_env.OS == 'linux' \
            else WindowsPackage.PACKAGE_LIST

        # Collect all packages with dependencies
        all_packages = {}
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

            # Collect this package and all its dependencies
            self.collect_dependencies(pkg, all_packages, package_list)

            # Store version for the explicitly requested package
            if name not in self.package_versions:
                self.package_versions[name] = version

        # Now check which packages need installation
        packages_to_install = {}

        for name, pkg in all_packages.items():
            version = self.package_versions.get(name, None)

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

        # Add packages to install to self.packages for display
        self.packages.update(packages_to_install)

        # If all packages are skipped, just display and return
        if not packages_to_install:
            console.print("[dim]All packages are already installed[/dim]")
            return

        # Sort packages by dependencies (dependencies first)
        try:
            sorted_packages = self.topological_sort(packages_to_install)
        except ValueError as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
            return

        # Install packages in parallel, respecting dependencies
        with Live(self.create_display(), refresh_per_second=10, console=Console()) as live:
            # Set up download callback to update the live display
            def update_display():
                live.update(self.create_display())

            # Track which packages are completed
            completed = set()
            error_occurred = False

            # Create batches of packages that can be installed in parallel
            def get_ready_packages():
                """Get packages whose dependencies are all completed"""
                ready = []
                for pkg in sorted_packages:
                    if pkg.name in completed:
                        continue

                    # Check if all dependencies are completed
                    deps_ready = True
                    if hasattr(pkg, 'dependencies') and pkg.dependencies:
                        for dep_class in pkg.dependencies:
                            if dep_class.name not in completed:
                                deps_ready = False
                                break

                    if deps_ready:
                        ready.append(pkg)

                return ready

            def install_package(pkg):
                """Install a single package"""
                version = self.package_versions.get(pkg.name, None)
                try:
                    pkg.download_callback = update_display
                    pkg.install(version, reinstall, refresh_cache)
                    pkg.download_callback = None
                    return (pkg.name, True, None)
                except Exception as e:
                    pkg.set_status("Error", "bold red")
                    pkg.logger.error(str(e))
                    return (pkg.name, False, e)

            # Install in waves until all packages are done
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                while len(completed) < len(sorted_packages) and not error_occurred:
                    ready = get_ready_packages()

                    if not ready:
                        # No packages ready but not all completed - circular dependency or error
                        break

                    # Submit all ready packages
                    futures = {executor.submit(install_package, pkg): pkg for pkg in ready}

                    # Wait for them to complete
                    for future in as_completed(futures):
                        pkg_name, success, error = future.result()
                        completed.add(pkg_name)
                        live.update(self.create_display())

                        if not success:
                            console.print(f"\n[bold red]Failed to install {pkg_name}: {error}[/bold red]")
                            console.print("[yellow]Stopping installation due to error[/yellow]")
                            error_occurred = True
                            break

    def create_display(self) -> Table:
        table = Table(show_header=False, show_edge=False, pad_edge=False, box=None, expand=False, collapse_padding=False)
        table.add_column("Package", min_width=15, no_wrap=True)
        table.add_column("Status", min_width=15, no_wrap=True)
        table.add_column("Progress", no_wrap=True, overflow="ellipsis", ratio=1)

        for name, pkg in self.packages.items():
            pkg_text = Text(f"📦 {name}", style='bold blue')
            status_text = Text(pkg.status, style=pkg.status_style)

            if pkg.download_progress is not None:
                # Render the Progress object directly
                from rich.console import Console
                from io import StringIO

                # Create a temporary console to render the progress
                temp_console = Console(file=StringIO(), force_terminal=True, width=80)
                temp_console.print(pkg.download_progress)
                progress_output = temp_console.file.getvalue().strip()

                progress_display = Text.from_ansi(progress_output)
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
