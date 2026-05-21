"""
Pulsar - A Python Package Manager CLI
"""
import os
import sys
import typing
import shutil
import pathlib

import typer

sys.path.append(
    os.environ.get(
        'PULSAR_ROOT', 
        os.path.join(os.path.dirname(__file__), '..')
    )
)

import pulsar_env
import shell_integration
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

library.import_all()

app = typer.Typer(
    name='pulsar',
    help="Pulsar - Python Package Manager",
    add_completion=True,
    rich_markup_mode='rich',
)

for spell_book in library.catalog.values():
    app.add_typer(spell_book.typer_app, rich_help_panel='Spell Books')


def show_banner():
    """Display a random Pulsar banner."""
    pulsar_console.console.print(ASCII_ART, style='bold blue', markup=False, highlight=False)
    pulsar_console.console.print(
        "By Andrew Ashby\n",
        style='dim blue'
    )


@app.command(hidden=True)
def activate():
    """
    Activate the Pulsar environment.
    """
    for sb in library.catalog.values():
        sb.on_activate()


@app.command()
def install(
    spell_books: typing.Optional[typing.List[str]] = typer.Argument(None, help="Spell Book(s) to install"),
    all: bool = typer.Option(False, '--all', '-a', help="Install all available spell books"),
    reinstall: bool = typer.Option(False, '--reinstall', '-r', help="Reinstall spell books"),
    refresh_cache: bool = typer.Option(False, '--refresh-cache', help="Redownload spell books"),
    workers: int = typer.Option(4, '--workers', '-w', help="Number of parallel workers")
):
    """
    Install one or more spell book.

    Example:
        pulsar install wezterm
        pulsar install lazygit fzf --reinstall
        pulsar install --all
    """

    import summoning_circle
    
    install_list = []

    if all:
        install_list = list(library.catalog.values())
    else:
        for name in spell_books:
            if name not in library.catalog:
                raise KeyError(f"Unable to find the spell book: '{name}'")
            
            install_list.append(library.catalog[name])

    summoning_circle.install_spell_books(
        install_list, reinstall, refresh_cache, workers
    )


@app.command()
def uninstall(
    spell_books: typing.Optional[typing.List[str]] = typer.Argument(None, help="Spell book(s) to uninstall"),
    all: bool = typer.Option(False, '--all', '-a', help="Uninstall all installed spell book"),
    yes: bool = typer.Option(False, '--yes', '-y', help="Skip confirmation"),
):
    """
    Uninstall one or more spell books.

    Example:
        pulsar uninstall wezterm
        pulsar uninstall nodejs python --yes
        pulsar uninstall --all --yes
    """
    
    if all:
        uninstall_list = list(library.catalog.values())
    else:
        uninstall_list = []
        for name in spell_books:
            if name not in library.catalog:
                raise KeyError(f"Unable to find spell book: '{name}'")
            uninstall_list.append(library.catalog[name])

    if not uninstall_list:
        typer.echo("No spell books to uninstall.")
        return

    # Show confirmation unless --yes is provided
    if not yes:
        typer.echo("The following spell books will be uninstalled:")
        for sb in uninstall_list:
            typer.echo(f"  - {sb.name}")

        confirm = typer.confirm("Do you want to continue?")
        if not confirm:
            typer.echo("Uninstall cancelled.")
            return

    for sb in uninstall_list:
        sb.uninstall()


# @app.command('list')
# def list_command(
#     versions: bool = typer.Option(False, '--versions', '-v', help="Show installed versions"),
#     include_uninstalled: bool = typer.Option(False, '--all', '-a', help="Show all spell books and if they are installed."),
# ):
#     """
#     List available spell books and their installation status.

#     Example:
#         pulsar list                    # List installed spell books
#         pulsar list --versions         # List with version numbers
#         pulsar list --all              # List all spell books
#     """
#     # Get spell books based on filter
#     if include_uninstalled:
#         spell_books = list(library.catalog.values())
#     else:
#         spell_books = [sb for sb in library.catalog.values() if sb.installed]

#     if not spell_books:
#         pulsar_console.console.print("[dim]No spell books found[/dim]\n")
#         return

#     # Sort by name
#     spell_books.sort(key=lambda sb: sb.name)

#     # Calculate column widths
#     max_name_len = max(len(sb.name) for sb in spell_books)
#     name_width = max(max_name_len, len("Spell Book"))

#     if versions or include_uninstalled:
#         # Header
#         if include_uninstalled:
#             pulsar_console.console.print(f"{'Spell Book':<{name_width}} {'Status':<12} Version")
#             pulsar_console.console.print(f"{'-' * name_width} {'-' * 12} {'-' * 10}")
#         else:
#             pulsar_console.console.print(f"{'Spell Book':<{name_width}} Version")
#             pulsar_console.console.print(f"{'-' * name_width} {'-' * 10}")

#         # Rows
#         for sb in spell_books:
#             version_str = sb.version if sb.version else "-"

#             if include_uninstalled:
#                 status_width = 12
#                 if sb.installed_with_pulsar:
#                     status_text = "installed"
#                     status = f"[green]{status_text:<{status_width}}[/green]"
#                 elif sb.installed:
#                     status_text = "system"
#                     status = f"[yellow]{status_text:<{status_width}}[/yellow]"
#                 else:
#                     status_text = "not installed"
#                     status = f"[dim]{status_text:<{status_width}}[/dim]"
#                     version_str = ""

#                 pulsar_console.console.print(f"{sb.name:<{name_width}} {status} {version_str}")
#             else:
#                 pulsar_console.console.print(f"{sb.name:<{name_width}} {version_str}")
        
#         pulsar_console.console.print()

#     else:
#         for sb in spell_books:
#             pulsar_console.console.print(f"{sb.name}")


@app.command()
def clean(
    cache: bool = typer.Option(False, '--cache', help="Clean cache directory"),
    data: bool = typer.Option(False, '--data', help="Clean data and state directories"),
    yes: bool = typer.Option(False, '--yes', '-y', help="Skip confirmation"),
):
    """
    Clean cache and/or data/state directories.

    Example:
        pulsar clean --cache            # Clean cache only
        pulsar clean --data             # Clean data and state
        pulsar clean --cache --data     # Clean cache and data
        pulsar clean --cache --yes      # Skip confirmation
    """

    # If neither flag is set, show error
    if not cache and not data:
        pulsar_console.console.print("[red]Error: Specify --cache and/or --data flag[/red]\n")
        raise typer.Exit(code=1)

    # Build list of directories to clean
    dirs_to_remove = []

    if cache:
        cache_dir = pathlib.Path(pulsar_env.PULSAR_CACHE_DIR)
        if cache_dir.exists():
            dirs_to_remove.append(cache_dir)

    if data:
        data_dir = pathlib.Path(pulsar_env.PULSAR_DATA_DIR)
        state_dir = pathlib.Path(pulsar_env.PULSAR_STATE_DIR)
        if data_dir.exists():
            dirs_to_remove.append(data_dir)
        if state_dir.exists():
            dirs_to_remove.append(state_dir)

    # If no directories exist, nothing to clean
    if not dirs_to_remove:
        pulsar_console.console.print("[dim]No directories to clean (they don't exist)[/dim]\n")
        return

    # Show what will be deleted
    pulsar_console.console.print(f"\n[bold yellow]⚠ WARNING:[/bold yellow] This will delete the following directories:")
    for d in dirs_to_remove:
        pulsar_console.console.print(f"  • {d}")
    pulsar_console.console.print()

    # Confirm unless --yes is provided
    if not yes:
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            pulsar_console.console.print("[dim]Clean cancelled[/dim]\n")
            raise typer.Exit(code=0)

    pulsar_console.console.print("[bold cyan]Cleaning directories...[/bold cyan]")

    # Remove directories
    for d in dirs_to_remove:
        pulsar_console.console.print(f"  Removing {d.name}...")
        shutil.rmtree(d)

    pulsar_console.console.print("[bold green]✓ Clean complete![/bold green]\n")


@app.command()
def reset(
    yes: bool = typer.Option(False, '--yes', '-y', help="Skip confirmation"),
):
    """
    Reset Pulsar environment by deleting bin and .venv directories.

    This will remove all installed packages and the virtual environment.
    The environment will be reinitialized on next activation.

    Example:
        pulsar reset
        pulsar reset --yes
    """
    dirs_to_remove = [
        pulsar_env.PULSAR_BIN_DIR,
        pulsar_env.VIRTUAL_ENV,
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
    yes: bool = typer.Option(False, '--yes', '-y', help="Skip confirmation"),
):
    """
    Completely nuke the Pulsar environment.

    This will delete all cache, data, state, bin, .venv, and __pycache__ directories.
    Use this for a complete clean slate.

    Example:
        pulsar nuke
        pulsar nuke --yes
    """

    dirs_to_remove = [
        pulsar_env.PULSAR_CACHE_DIR,
        pulsar_env.PULSAR_DATA_DIR,
        pulsar_env.PULSAR_STATE_DIR,
        pulsar_env.PULSAR_BIN_DIR,
        pulsar_env.VIRTUAL_ENV,
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
    for pycache_dir in pulsar_env.PULSAR_ROOT.rglob('__pycache__'):
        try:
            shutil.rmtree(pycache_dir)
        except Exception:
            pass

    pulsar_console.console.print("[bold green]✓ Nuke complete![/bold green]")
    pulsar_console.console.print("[dim]Run 'source activate' to reinitialize the environment.[/dim]\n")


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


def __flush_enchantments(*args, **kwargs):
    shell_integration.enchant_shell()


@app.callback(invoke_without_command=True, result_callback=__flush_enchantments)
def main(
    ctx: typer.Context,
    display_banner: bool = typer.Option(True, '--banner/--no-banner', help="Show ASCII banner"),
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



if __name__ == '__main__':
    app()

