"""
Pulsar - A Python Package Manager CLI
"""
import os
import sys
import random

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


sys.path.append(
    os.environ.get(
        'PULSAR_ROOT', 
        os.path.join(os.path.dirname(__file__), '..')
    )
)

from src import pulsar_env
from src.package_classes import LinuxPackage, WindowsPackage
from src.package_installer import PackageInstaller
from src.packages import *

app = typer.Typer(
    name="pulsar",
    help="⭐ Pulsar - Python Package Manager",
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()

ASCII_ARTS = [
r'''


╔═║║ ║║  ╔═╝╔═║╔═║
╔═╝║ ║║  ══║╔═║╔╔╝
╝  ══╝══╝══╝╝ ╝╝ ╝


''',

r'''

    ___             _
   | _ \   _  _    | |     ___    __ _      _ _
   |  _/  | +| |   | |    (_-<   / _` |    | '_|
  _|_|_   _\_,_|  _|_|_   /__/_  \__,_|   _|_|_
_| """ |_|"""""|_|"""""|_|"""""|_|"""""|_|"""""|
"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'
''',

r'''
    ___       ___       ___       ___       ___       ___
   /\  \     /\__\     /\__\     /\  \     /\  \     /\  \
  /::\  \   /:/ _/_   /:/  /    /::\  \   /::\  \   /::\  \
 /::\:\__\ /:/_/\__\ /:/__/    /\:\:\__\ /::\:\__\ /::\:\__\
 \/\::/  / \:\/:/  / \:\  \    \:\:\/__/ \/\::/  / \;:::/  /
    \/__/   \::/  /   \:\__\    \::/  /    /:/  /   |:\/__/
             \/__/     \/__/     \/__/     \/__/     \|__|
''',

r'''


╭─╮╷ ╷╷  ╭─╮╭─╮╭─╮
├─╯│ ││  ╰─╮├─┤├┬╯
╵  ╰─╯╰─╴╰─╯╵ ╵╵╰╴

''',

r'''
      :::::::::  :::    ::: :::        ::::::::      :::     :::::::::
     :+:    :+: :+:    :+: :+:       :+:    :+:   :+: :+:   :+:    :+:
    +:+    +:+ +:+    +:+ +:+       +:+         +:+   +:+  +:+    +:+
   +#++:++#+  +#+    +:+ +#+       +#++:++#++ +#++:++#++: +#++:++#:
  +#+        +#+    +#+ +#+              +#+ +#+     +#+ +#+    +#+
 #+#        #+#    #+# #+#       #+#    #+# #+#     #+# #+#    #+#
###         ########  ########## ########  ###     ### ###    ###
''',

r'''

8""""8
8    8 e   e e     eeeee eeeee eeeee
8eeee8 8   8 8     8   " 8   8 8   8
88     8e  8 8e    8eeee 8eee8 8eee8e
88     88  8 88       88 88  8 88   8
88     88ee8 88eee 8ee88 88  8 88   8
''',

r'''

     _/\/\/\/\/\________________/\/\_______________________________________
    _/\/\____/\/\__/\/\__/\/\__/\/\______/\/\/\/\____/\/\/\____/\/\__/\/\_
   _/\/\/\/\/\____/\/\__/\/\__/\/\____/\/\/\/\____/\____/\____/\/\/\/\___
  _/\/\__________/\/\__/\/\__/\/\__________/\/\__/\____/\____/\/\_______
 _/\/\____________/\/\/\/\__/\/\/\__/\/\/\/\______/\/\/\/\__/\/\_______
______________________________________________________________________
''',

r'''


   _ \          |
  |   |  |   |  |   __|   _` |   __|
  ___/   |   |  | \__ \  (   |  |
 _|     \__,_| _| ____/ \__,_| _|

''',
]


def show_banner():
    """Display a random Pulsar banner."""
    ascii_art = random.choice(ASCII_ARTS)
    console.print(ascii_art, style="bold blue", markup=False, highlight=False)
    console.print(
        "By Andrew Ashby\n",
        style="dim blue"
    )

@app.command()
def activate():
    """
    🎉 Activate the Pulsar environment.

    Example:
        pulsar activate
    """

    if pulsar_env.OS == 'linux':
        script: list[str] = []
        for k, v in pulsar_env.ACTIVATION_VARS.items():
            script.append(f"export {k}={v}")

        console.print('\n'.join(script))
        return


@app.command()
def install(
    packages: list[str] = typer.Argument(..., help="Package(s) to install"),
    reinstall: bool = typer.Option(False, '--reinstall', '-r', help="Reinstall package"),
    refresh_cache: bool = typer.Option(False, '--refresh-cache', help="Redownload package"),
    workers: int = typer.Option(4, '--workers', '-w', help="Number of parallel workers")
):
    """
    📦 Install one or more packages.

    Example:
        pulsar install wezterm
        pulsar install lazygit fzf --reinstall
        pulsar install go==1.21.0
    """

    package_list = LinuxPackage.PACKAGE_LIST if pulsar_env.OS == 'linux' else WindowsPackage.PACKAGE_LIST

    # Validate all packages exist before starting installation
    for package_str in packages:
        package_name = package_str.split('==')[0].lower() if '==' in package_str else package_str.lower()

        if package_name not in package_list:
            console.print(f"[red]✗ Error: Package '{package_name}' not found[/red]")
            console.print(f"[dim]Available packages: {', '.join(package_list.keys())}[/dim]")
            raise typer.Exit(code=1)

    console.print(f"\n[bold cyan]Installing packages:[/bold cyan] {', '.join(packages)}\n")

    # Create installer and install packages
    try:
        installer = PackageInstaller(max_workers=workers)
        installer.install_packages(packages, reinstall=reinstall, refresh_cache=refresh_cache)
        console.print("\n[green]✓ Installation complete![/green]\n")
    except Exception as e:
        console.print(f"\n[red]✗ Installation failed: {e}[/red]\n")
        raise typer.Exit(code=1)


@app.command()
def uninstall(
    packages: List[str] = typer.Argument(..., help="Package(s) to uninstall"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    🗑️  Uninstall one or more packages.

    Example:
        pulsar uninstall wezterm
        pulsar uninstall nodejs python --yes
    """
    package_list = LinuxPackage.PACKAGE_LIST if pulsar_env.OS == 'linux' else WindowsPackage.PACKAGE_LIST

    # Validate all packages exist
    for package_name in packages:
        package_name = package_name.lower()
        if package_name not in package_list:
            console.print(f"[red]✗ Error: Package '{package_name}' not found[/red]")
            console.print(f"[dim]Available packages: {', '.join(package_list.keys())}[/dim]")
            raise typer.Exit(code=1)

    console.print(f"\n[bold red]Uninstalling packages:[/bold red] {', '.join(packages)}\n")

    # Check which packages are actually installed
    to_uninstall = []
    for package_name in packages:
        package_name = package_name.lower()
        pkg = package_list[package_name]
        if pkg.is_installed_with_pulsar():
            to_uninstall.append(package_name)
            console.print(f"  • {package_name} - [green]installed[/green]")
        else:
            console.print(f"  • {package_name} - [dim]not installed[/dim]")

    if not to_uninstall:
        console.print("\n[yellow]No packages to uninstall.[/yellow]\n")
        return

    console.print()

    if not yes:
        confirm = typer.confirm(f"Are you sure you want to uninstall {len(to_uninstall)} package(s)?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]\n")
            raise typer.Abort()

    # Uninstall each package
    success_count = 0
    error_count = 0

    for package_name in to_uninstall:
        pkg = package_list[package_name]
        try:
            console.print(f"[cyan]Uninstalling {package_name}...[/cyan]")
            pkg.uninstall()
            console.print(f"[green]✓ {package_name} uninstalled successfully[/green]")
            success_count += 1
        except Exception as e:
            console.print(f"[red]✗ Failed to uninstall {package_name}: {e}[/red]")
            error_count += 1

    console.print()
    if error_count == 0:
        console.print(f"[green]✓ Successfully uninstalled {success_count} package(s)![/green]\n")
    else:
        console.print(f"[yellow]⚠ Uninstalled {success_count} package(s), {error_count} failed[/yellow]\n")
        raise typer.Exit(code=1)


# @app.command()
# def update(
#     packages: Optional[List[str]] = typer.Argument(None, help="Specific package(s) to update"),
#     all: bool = typer.Option(False, "--all", "-a", help="Update all packages"),
# ):
#     """
#     🔄 Update packages to their latest versions.

#     Example:
#         pulsar update requests
#         pulsar update --all
#     """
#     if all:
#         console.print("\n[bold cyan]Updating all packages...[/bold cyan]")
#     elif packages:
#         console.print(f"\n[bold cyan]Updating packages:[/bold cyan] {', '.join(packages)}")
#     else:
#         console.print("[red]Error: Specify packages or use --all flag[/red]\n")
#         raise typer.Exit(code=1)

#     # TODO: Implement package update logic
#     console.print("[yellow]⚠ Update logic not yet implemented[/yellow]\n")


@app.command()
def list(
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, simple"),
    installed_only: bool = typer.Option(False, "--installed", "-i", help="Show only installed packages"),
):
    """
    📋 List available and installed packages.

    Example:
        pulsar list
        pulsar list --installed
        pulsar list --format json
        pulsar list --format simple
    """
    package_list = LinuxPackage.PACKAGE_LIST if pulsar_env.OS == 'linux' else WindowsPackage.PACKAGE_LIST

    # Gather package information
    packages_info = []
    for name, pkg_class in package_list.items():
        # Skip the base class
        if name in ['LinuxPackage', 'WindowsPackage']:
            continue

        is_installed = pkg_class.is_installed_with_pulsar()

        # Skip if filtering for installed only
        if installed_only and not is_installed:
            continue

        version = pkg_class.get_version() if is_installed else "-"
        status = "Installed" if is_installed else "Not installed"

        packages_info.append({
            'name': name,
            'description': pkg_class.description,
            'version': version,
            'installed': is_installed,
            'status': status,
        })

    # Sort by name
    packages_info.sort(key=lambda x: x['name'])

    if not packages_info:
        if installed_only:
            console.print("\n[yellow]No packages are currently installed.[/yellow]\n")
        else:
            console.print("\n[yellow]No packages available.[/yellow]\n")
        return

    # Output based on format
    if format == "json":
        import json
        console.print(json.dumps(packages_info, indent=2))

    elif format == "simple":
        console.print()
        for pkg in packages_info:
            status_symbol = "✓" if pkg['installed'] else " "
            version_str = f" ({pkg['version']})" if pkg['installed'] else ""
            console.print(f"{status_symbol} {pkg['name']}{version_str}")
        console.print()

    else:  # table format (default)
        console.print("\n[bold cyan]Available Packages[/bold cyan]\n")

        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Version", style="green")
        table.add_column("Status", style="yellow")

        for pkg in packages_info:
            status_style = "green" if pkg['installed'] else "dim"
            table.add_row(
                pkg['name'],
                pkg['description'],
                pkg['version'],
                f"[{status_style}]{pkg['status']}[/{status_style}]"
            )

        console.print(table)
        console.print()

        # Summary
        installed_count = sum(1 for p in packages_info if p['installed'])
        total_count = len(packages_info)
        console.print(f"[dim]{installed_count} installed / {total_count} available[/dim]\n")



@app.command()
def clean(
    data: bool = typer.Option(False, "--data", help="Also clean data and state directories"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    🧹 Clean cache and optionally data/state directories.

    Example:
        pulsar clean                    # Clean cache only
        pulsar clean --data             # Clean cache, data, and state
        pulsar clean --yes              # Skip confirmation
    """
    import shutil
    from pathlib import Path

    console.print("\n[bold cyan]Cleaning Pulsar directories...[/bold cyan]\n")

    # Determine what to clean
    dirs_to_clean = []

    # Always clean cache
    cache_dir = Path(pulsar_env.PULSAR_CACHE_DIR)
    if cache_dir.exists():
        dirs_to_clean.append(("Cache", cache_dir))

    # Optionally clean data and state
    if data:
        data_dir = Path(pulsar_env.PULSAR_DATA_DIR)
        state_dir = Path(pulsar_env.PULSAR_STATE_DIR)

        if data_dir.exists():
            dirs_to_clean.append(("Data", data_dir))

        if state_dir.exists():
            dirs_to_clean.append(("State", state_dir))

    if not dirs_to_clean:
        console.print("[yellow]No directories to clean.[/yellow]\n")
        return

    # Show what will be cleaned
    console.print("The following directories will be cleaned:\n")
    total_size = 0

    for name, dir_path in dirs_to_clean:
        # Calculate directory size
        size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
        size_mb = size / (1024 * 1024)
        total_size += size

        console.print(f"  • {name:10s} {dir_path}")
        console.print(f"    [dim]Size: {size_mb:.2f} MB[/dim]")

    total_size_mb = total_size / (1024 * 1024)
    console.print(f"\n[bold]Total size: {total_size_mb:.2f} MB[/bold]\n")

    # Confirm
    if not yes:
        confirm = typer.confirm("Are you sure you want to delete these directories?")
        if not confirm:
            console.print("[yellow]Aborted.[/yellow]\n")
            raise typer.Abort()

    # Clean directories
    console.print()
    success_count = 0
    error_count = 0

    for name, dir_path in dirs_to_clean:
        try:
            console.print(f"[cyan]Cleaning {name}...[/cyan]")

            # Remove all contents but keep the directory
            for item in dir_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            console.print(f"[green]✓ {name} cleaned[/green]")
            success_count += 1
        except Exception as e:
            console.print(f"[red]✗ Failed to clean {name}: {e}[/red]")
            error_count += 1

    console.print()
    if error_count == 0:
        console.print(f"[green]✓ Successfully cleaned {success_count} director{'y' if success_count == 1 else 'ies'}![/green]\n")
        console.print(f"[dim]Freed {total_size_mb:.2f} MB of disk space[/dim]\n")
    else:
        console.print(f"[yellow]⚠ Cleaned {success_count} director{'y' if success_count == 1 else 'ies'}, {error_count} failed[/yellow]\n")
        raise typer.Exit(code=1)


# @app.command()
# def run(
#     script: str = typer.Argument(..., help="Script name to run"),
#     args: Optional[List[str]] = typer.Argument(None, help="Arguments to pass to script"),
# ):
#     """
#     🚀 Run a script defined in your project.

#     Example:
#         pulsar run dev
#         pulsar run test --coverage
#     """
#     console.print(f"\n[bold cyan]Running script:[/bold cyan] {script}\n")

#     if args:
#         console.print(f"[dim]Arguments: {' '.join(args)}[/dim]\n")

#     # TODO: Implement script execution logic
#     console.print("[yellow]⚠ Run logic not yet implemented[/yellow]\n")


@app.command()
def version(
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all version info"),
):
    """
    📌 Show Pulsar version.
    """
    console.print("\n[bold cyan]Pulsar Package Manager[/bold cyan]")
    console.print("[green]Version:[/green] 0.1.0\n")

    if show_all:
        console.print("[dim]Python: 3.12+[/dim]")
        console.print("[dim]Platform: Cross-platform[/dim]\n")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    display_banner: bool = typer.Option(True, "--banner/--no-banner", help="Show ASCII banner"),
):
    """
    ⭐ Pulsar - Python Package Manager

    A modern, fast Python package manager with a beautiful CLI interface.
    """
    if ctx.invoked_subcommand is None:
        if display_banner:
            show_banner()
        console.print("[bold]Usage:[/bold] pulsar [COMMAND] [OPTIONS]\n")
        console.print("Run [cyan]pulsar --help[/cyan] for more information.\n")


if __name__ == "__main__":
    app()
