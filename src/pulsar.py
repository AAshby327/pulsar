"""
Pulsar - A Python Package Manager CLI
"""
import os
import sys
import typing

import typer

sys.path.append(
    os.environ.get(
        'PULSAR_ROOT', 
        os.path.join(os.path.dirname(__file__), '..')
    )
)

import pulsar_env
import pulsar_console
import library

ASCII_ART = \
r'''
      :::::::::  :::    ::: :::        ::::::::      :::     :::::::::
     :+:    :+: :+:    :+: :+:       :+:    :+:   :+: :+:   :+:    :+:
    +:+    +:+ +:+    +:+ +:+       +:+         +:+   +:+  +:+    +:+
   +#++:++#+  +#+    +:+ +#+       +#++:++#++ +#++:++#++: +#++:++#:
  +#+        +#+    +#+ +#+              +#+ +#+     +#+ +#+    +#+
 #+#        #+#    #+# #+#       #+#    #+# #+#     #+# #+#    #+#
###         ########  ########## ########  ###     ### ###    ###
'''

app = typer.Typer(
    name="pulsar",
    help="Pulsar - Python Package Manager",
    add_completion=True,
    rich_markup_mode="rich",
)

library.SpellBook.import_all()

for spell_book in library.SpellBook.CATALOG.values():
    app.add_typer(spell_book.typer_app, rich_help_panel='Spell Books')


def show_banner():
    """Display a random Pulsar banner."""
    pulsar_console.console.print(ASCII_ART, style="bold blue", markup=False, highlight=False)
    pulsar_console.console.print(
        "By Andrew Ashby\n",
        style="dim blue"
    )


@app.command()
def activate():
    """
    Activate the Pulsar environment.
    """
    pass


@app.command()
def install(
    packages: typing.Optional[typing.List[str]] = typer.Argument(None, help="Package(s) to install"),
    all: bool = typer.Option(False, '--all', '-a', help="Install all available packages"),
    reinstall: bool = typer.Option(False, '--reinstall', '-r', help="Reinstall package"),
    refresh_cache: bool = typer.Option(False, '--refresh-cache', help="Redownload package"),
    workers: int = typer.Option(4, '--workers', '-w', help="Number of parallel workers")
):
    """
    Install one or more packages.

    Example:
        pulsar install wezterm
        pulsar install lazygit fzf --reinstall
        pulsar install --all
    """
    pass


@app.command()
def uninstall(
    packages: typing.Optional[typing.List[str]] = typer.Argument(None, help="Package(s) to uninstall"),
    all: bool = typer.Option(False, "--all", "-a", help="Uninstall all installed packages"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Uninstall one or more packages.

    Example:
        pulsar uninstall wezterm
        pulsar uninstall nodejs python --yes
        pulsar uninstall --all --yes
    """
    pass


# @app.command()
# def update(
#     packages: Optional[List[str]] = typer.Argument(None, help="Specific package(s) to update"),
#     all: bool = typer.Option(False, "--all", "-a", help="Update all packages"),
# ):
#     """
#     Update packages to their latest versions.

#     Example:
#         pulsar update requests
#         pulsar update --all
#     """
#     if all:
#         pulsar_console.console.print("\n[bold cyan]Updating all packages...[/bold cyan]")
#     elif packages:
#         pulsar_console.console.print(f"\n[bold cyan]Updating packages:[/bold cyan] {', '.join(packages)}")
#     else:
#         pulsar_console.console.print("[red]Error: Specify packages or use --all flag[/red]\n")
#         raise typer.Exit(code=1)

#     # TODO: Implement package update logic
#     pulsar_console.console.print("[yellow]⚠ Update logic not yet implemented[/yellow]\n")


@app.command()
def list(
    format: str = typer.Option("simple", "--format", "-f", help="Output format: table, json, simple"),
    installed_only: bool = typer.Option(False, "--installed", "-i", help="Show only installed packages"),
):
    """
    List available and installed packages.

    Example:
        pulsar list
        pulsar list --installed
        pulsar list --format json
        pulsar list --format simple
    """
    pass



@app.command()
def clean(
    cache: bool = typer.Option(False, "--cache", help="Clean cache directory"),
    data: bool = typer.Option(False, "--data", help="Clean data and state directories"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Clean cache and/or data/state directories.

    Example:
        pulsar clean --cache            # Clean cache only
        pulsar clean --data             # Clean data and state
        pulsar clean --cache --data     # Clean cache and data
        pulsar clean --cache --yes      # Skip confirmation
    """
    pass


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Reset Pulsar environment by deleting bin and .venv directories.

    This will remove all installed packages and the virtual environment.
    The environment will be reinitialized on next activation.

    Example:
        pulsar reset
        pulsar reset --yes
    """
    import shutil
    from pathlib import Path

    pulsar_root = Path(pulsar_env.PULSAR_ROOT)
    dirs_to_remove = [
        pulsar_root / 'bin',
        pulsar_root / '.venv',
    ]

    pulsar_console.console.print(f"\n[bold yellow]⚠ WARNING:[/bold yellow] This will delete the following directories:")
    for d in dirs_to_remove:
        pulsar_console.console.print(f"  • {d}")
    pulsar_console.console.print()

    if not yes:
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            pulsar_console.console.print("[dim]Reset cancelled[/dim]\n")
            raise typer.Exit(code=0)

    pulsar_console.console.print("[bold cyan]Resetting Pulsar environment...[/bold cyan]")

    for d in dirs_to_remove:
        if d.exists():
            pulsar_console.console.print(f"  Removing {d.name}...")
            shutil.rmtree(d)

    pulsar_console.console.print("[bold green]✓ Reset complete![/bold green]")
    pulsar_console.console.print("[dim]Run 'source activate' to reinitialize the environment.[/dim]\n")


@app.command()
def nuke(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """
    Completely nuke the Pulsar environment.

    This will delete all cache, data, state, bin, .venv, and __pycache__ directories.
    Use this for a complete clean slate.

    Example:
        pulsar nuke
        pulsar nuke --yes
    """
    import shutil
    from pathlib import Path

    pulsar_root = Path(pulsar_env.PULSAR_ROOT)
    dirs_to_remove = [
        pulsar_root / '.cache',
        pulsar_root / '.data',
        pulsar_root / '.state',
        pulsar_root / 'bin',
        pulsar_root / '.venv',
    ]

    pulsar_console.console.print(f"\n[bold red]⚠ WARNING:[/bold red] This will delete the following directories:")
    for d in dirs_to_remove:
        pulsar_console.console.print(f"  • {d}")
    pulsar_console.console.print("  • All __pycache__ directories")
    pulsar_console.console.print()

    if not yes:
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            pulsar_console.console.print("[dim]Nuke cancelled[/dim]\n")
            raise typer.Exit(code=0)

    pulsar_console.console.print("[bold cyan]Nuking Pulsar environment...[/bold cyan]")

    # Remove main directories
    for d in dirs_to_remove:
        if d.exists():
            pulsar_console.console.print(f"  Removing {d.name}...")
            shutil.rmtree(d)

    # Remove all __pycache__ directories
    pulsar_console.console.print("  Removing __pycache__ directories...")
    for pycache_dir in pulsar_root.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache_dir)
        except Exception:
            pass

    pulsar_console.console.print("[bold green]✓ Nuke complete![/bold green]")
    pulsar_console.console.print("[dim]Run 'source activate' to reinitialize the environment.[/dim]\n")

# @app.command()
# def launch():
#     """
#     Launch WezTerm in a detached window.

#     Example:
#         pulsar launch
#     """
#     from pathlib import Path

#     package_list = get_all_packages()

#     # Check if wezterm package exists
#     if 'wezterm' not in package_list:
#         pulsar_console.console.print("\n[red]✗ Error: WezTerm package not found in package list[/red]\n")
#         raise typer.Exit(code=1)

#     wezterm_pkg = package_list['wezterm']

#     # Check if wezterm is installed with pulsar
#     if not wezterm_pkg.is_installed_with_pulsar():
#         pulsar_console.console.print("\n[yellow]⚠ WezTerm is not installed with Pulsar.[/yellow]")
#         install_prompt = typer.confirm("Would you like to install WezTerm now?")

#         if not install_prompt:
#             pulsar_console.console.print("[dim]Exiting...[/dim]\n")
#             raise typer.Exit(code=0)

#         # Install wezterm
#         pulsar_console.console.print("\n[bold cyan]Installing WezTerm...[/bold cyan]\n")
#         try:
#             installer = PackageInstaller(max_workers=1)
#             installer.install_packages(['wezterm'], reinstall=False, refresh_cache=False)
#         except Exception as e:
#             pulsar_console.console.print(f"\n[red]✗ Installation failed: {e}[/red]\n")
#             raise typer.Exit(code=1)

#     # Launch wezterm from bin directory
#     wezterm_bin = Path(pulsar_env.PULSAR_BIN_DIR) / 'wezterm' / ('wezterm.exe' if pulsar_env.OS == 'windows' else 'wezterm')

#     if not wezterm_bin.exists():
#         pulsar_console.console.print(f"\n[red]✗ WezTerm executable not found at: {wezterm_bin}[/red]\n")
#         raise typer.Exit(code=1)

#     try:
#         if pulsar_env.OS == 'windows':
#             # Windows: Use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS flags
#             DETACHED_PROCESS = 0x00000008
#             CREATE_NEW_PROCESS_GROUP = 0x00000200

#             subprocess.Popen(
#                 [str(wezterm_bin)],
#                 creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
#                 stdin=subprocess.DEVNULL,
#                 stdout=subprocess.DEVNULL,
#                 stderr=subprocess.DEVNULL,
#                 close_fds=True
#             )
#         else:
#             # Linux/Unix: Use nohup-style detachment
#             subprocess.Popen(
#                 [str(wezterm_bin)],
#                 stdin=subprocess.DEVNULL,
#                 stdout=subprocess.DEVNULL,
#                 stderr=subprocess.DEVNULL,
#                 start_new_session=True,
#                 close_fds=True
#             )

#     except Exception as e:
#         pulsar_console.console.print(f"\n[red]✗ Failed to launch WezTerm: {e}[/red]\n")
#         raise typer.Exit(code=1)


@app.command()
def version():
    """
    Show Pulsar version.
    """
    import tomllib

    pyproject_path = os.path.join(os.path.dirname(__file__), 'pyproject.toml')

    with open(pyproject_path, 'rb') as f:
        data = tomllib.load(f)
        version_str = data.get('project', {}).get('version', 'unknown')
        pulsar_console.console.print(f"Pulsar version: [bold cyan]{version_str}[/bold cyan]")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    display_banner: bool = typer.Option(True, "--banner/--no-banner", help="Show ASCII banner"),
):
    """
    Pulsar - Python Package Manager

    A modern, fast Python package manager with a beautiful CLI interface.
    """
    if ctx.invoked_subcommand is None:
        if display_banner:
            show_banner()
        pulsar_console.console.print("[bold]Usage:[/bold] pulsar [COMMAND] [OPTIONS]\n")
        pulsar_console.console.print("Run [cyan]pulsar --help[/cyan] for more information.\n")


if __name__ == "__main__":
    app()