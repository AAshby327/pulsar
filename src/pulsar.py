"""
Pulsar - A Python Package Manager CLI
"""
import typing
import time
start_time = time.time()

import typer

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

app = typer.Typer(
    name='pulsar',
    help="Pulsar - Python Package Manager",
    add_completion=True,
    rich_markup_mode='rich',
)

def show_banner():
    """Display a random pulsar banner."""
    pulsar_console.console.print(ASCII_ART, style='bold blue', markup=False, highlight=False)
    pulsar_console.console.print(
        "By Andrew Ashby\n",
        style='dim blue'
    )


@app.command(hidden=True)
def activate():
    """
    Activate the pulsar environment.
    """

    if pulsar_env.SHELL == 'bash':
        pulsar_env.add_source_file(
            pulsar_env.PULSAR_CONFIG_DIR / 'bash' / 'bashrc.sh'
        )
    elif pulsar_env.SHELL == 'powershell':
        pulsar_env.add_source_file(
            pulsar_env.PULSAR_CONFIG_DIR / 'powershell' / 'pwshrc.ps1'
        )

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
    already_installed = []

    if all:
        install_list = list(library.catalog.values())
    else:
        for name in spell_books:
            if name not in library.catalog:
                raise KeyError(f"Unable to find the spell book: '{name}'")
            
            sb = library.catalog[name]

            if not reinstall and sb.is_installed():
                already_installed.append(sb)
            else:
                install_list.append(sb)

    if len(already_installed) > 0:
        pulsar_console.console.print("[green]Already installed:[/green]")
        for sb in already_installed:
            pulsar_console.console.print(f"[green] ✓ {sb.name}[/green]")

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


@app.command('list')
def list_command(
    versions: bool = typer.Option(False, '--versions', '-v', help="Show installed versions"),
    include_uninstalled: bool = typer.Option(False, '--all', '-a', help="Show all spell books and if they are installed."),
):
    """
    List available spell books and their installation status.

    Example:
        pulsar list                    # List installed spell books
        pulsar list --versions         # List with version numbers
        pulsar list --all              # List all spell books
    """
    # Get spell books based on filter
    if include_uninstalled:
        spell_books = list(library.catalog.values())
    else:
        spell_books = [sb for sb in library.catalog.values() if sb.installed()]

    if not spell_books:
        pulsar_console.console.print("[dim]No spell books found[/dim]\n")
        return

    # Sort by name
    spell_books.sort(key=lambda sb: sb.name)

    # Calculate column widths
    max_name_len = max(len(sb.name) for sb in spell_books)
    name_width = max(max_name_len, len("Spell Book"))

    if versions or include_uninstalled:
        # Header
        if include_uninstalled:
            pulsar_console.console.print(f"{'Spell Book':<{name_width}}   {'Status':<12}   Version")
            pulsar_console.console.print(f"{'-' * name_width}   {'-' * 12}   {'-' * 10}")
        else:
            pulsar_console.console.print(f"{'Spell Book':<{name_width}}   Version")
            pulsar_console.console.print(f"{'-' * name_width}   {'-' * 10}")

        # Rows
        for sb in spell_books:
            # version_str = sb.version if sb.version else "-"
            version_str = sb.version()
            if not version_str: version_str = '-'

            if include_uninstalled:
                status_width = 12
                if sb.installed_with_pulsar():
                    status_text = "installed"
                    status = f"[green]{status_text:<{status_width}}[/green]"
                elif sb.installed():
                    status_text = "system"
                    status = f"[yellow]{status_text:<{status_width}}[/yellow]"
                else:
                    status_text = "not installed"
                    status = f"[dim]{status_text:<{status_width}}[/dim]"
                    version_str = ""

                pulsar_console.console.print(f"{sb.name:<{name_width}}   {status}   {version_str}")
            else:
                pulsar_console.console.print(f"{sb.name:<{name_width}}   {version_str}")
        
        pulsar_console.console.print()

    else:
        for sb in spell_books:
            pulsar_console.console.print(f"{sb.name}")


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
    import pathlib

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
    pulsar_env.remove_directories(*dirs_to_remove)

    pulsar_console.console.print("[bold green]✓ Clean complete![/bold green]\n")


@app.command()
def reset(
    yes: bool = typer.Option(False, '--yes', '-y', help="Skip confirmation"),
):
    """
    Reset pulsar environment by deleting bin and .venv directories.

    This will remove all installed packages and the virtual environment.
    The environment will be reinitialized on next activation.

    Example:
        pulsar reset
        pulsar reset --yes
    """
    dirs_to_remove = [
        pulsar_env.PULSAR_BIN_DIR,
        pulsar_env.PULSAR_VENV_DIR,
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

    pulsar_console.console.print("[bold cyan]Resetting pulsar environment...[/bold cyan]")
    pulsar_env.remove_directories(*dirs_to_remove)

    pulsar_console.console.print("[bold green]✓ Reset complete![/bold green]")
    pulsar_console.console.print("[dim]Run 'source activate' to reinitialize the environment.[/dim]\n")


@app.command()
def nuke(
    yes: bool = typer.Option(False, '--yes', '-y', help="Skip confirmation"),
):
    """
    Completely nuke the pulsar environment.

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
        pulsar_env.PULSAR_VENV_DIR,
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

    pulsar_console.console.print("[bold cyan]Nuking pulsar environment...[/bold cyan]")

    pulsar_env.remove_directories(*dirs_to_remove)

    pulsar_console.console.print("  Removing __pycache__ directories...")
    pulsar_env.remove_directories(*tuple(pulsar_env.PULSAR_SRC_DIR.rglob('__pycache__')))

    pulsar_console.console.print("[bold green]✓ Nuke complete![/bold green]")
    pulsar_console.console.print("[dim]Run 'source activate' to reinitialize the environment.[/dim]\n")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True}, add_help_option=False)
def uv(
    ctx: typer.Context,
):
    """
    Wrapper for the pulsar uv project.
    """
    import os
    import pathlib
    import subprocess

    exe_name = 'uv.exe' if pulsar_env.OS == 'windows' else 'uv'
    uv_bin = pathlib.Path(pulsar_env.PULSAR_BIN_DIR) / exe_name

    if not uv_bin.exists():
        pulsar_console.console.print("[red]UV is not installed.[/red]")
        raise typer.Exit(code=1)

    # Save previous environment variables
    prev_uv_project_environment = os.environ.get('UV_PROJECT_ENVIRONMENT')
    prev_virtual_env = os.environ.get('VIRTUAL_ENV')
    prev_uv_working_dir = os.environ.get('UV_WORKING_DIR')

    try:
        # Set pulsar UV environment
        os.environ['UV_PROJECT_ENVIRONMENT'] = str(pulsar_env.PULSAR_VENV_DIR)
        os.environ['VIRTUAL_ENV'] = str(pulsar_env.PULSAR_VENV_DIR)
        os.environ['UV_WORKING_DIR'] = str(pulsar_env.PULSAR_SRC_DIR)

        # Forward all arguments to uv
        result = subprocess.run([str(uv_bin)] + ctx.args)
        raise typer.Exit(code=result.returncode)

    finally:
        # Restore or unset environment variables
        if prev_uv_project_environment is not None:
            os.environ['UV_PROJECT_ENVIRONMENT'] = prev_uv_project_environment
        else:
            os.environ.pop('UV_PROJECT_ENVIRONMENT', None)

        if prev_virtual_env is not None:
            os.environ['VIRTUAL_ENV'] = prev_virtual_env
        else:
            os.environ.pop('VIRTUAL_ENV', None)

        if prev_uv_working_dir is not None:
            os.environ['UV_WORKING_DIR'] = prev_uv_working_dir
        else:
            os.environ.pop('UV_WORKING_DIR', None)


@app.command()
def version():
    """
    Show pulsar version.
    """
    import tomllib

    pyproject_path = pulsar_env.PULSAR_SRC_DIR / 'pyproject.toml'

    with open(pyproject_path, 'rb') as f:
        data = tomllib.load(f)
        version_str = data.get('project', {}).get('version', 'unknown')
        pulsar_console.console.print(f"pulsar version: [bold cyan]{version_str}[/bold cyan]")


def __flush_enchantments(*args, **kwargs):
    shell_integration.enchant_shell()
    if pulsar_env.PULSAR_DEBUG:
        exe_time_ms = (time.time() - start_time) * 1000
        pulsar_console.console.print(f"Finished in {exe_time_ms:.2f}ms", style='dim')


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
    library.import_all()
    for spell_book in library.catalog.values():
        app.add_typer(spell_book.typer_app, rich_help_panel='Spell Books')
    app()
