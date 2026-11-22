import os
import typing
import pathlib

import typer
import typer.core
from rich.console import Console

from pulsar.library import SpellBook

stdout = Console()
stderr = Console(stderr=True)

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

SUPPORTED_PLATFORMS = ('win-x86_64', 'linux-x86_64', 'linux-arm_64')

PLATFORM: typing.Literal['win-x86_64', 'linux-x86_64', 'linux-arm_64'] \
                = os.environ['PLATFORM']
ROOT_DIR =      pathlib.Path(os.environ['PULSAR_ROOT'])
CONFIG_DIR =    pathlib.Path(os.environ['PULSAR_CONFIG_DIR'])
SRC_DIR =       pathlib.Path(os.environ['PULSAR_SRC_DIR'])
BIN_DIR =       pathlib.Path(os.environ['PULSAR_BIN_DIR'])
DATA_DIR =      pathlib.Path(os.environ['PULSAR_DATA_DIR'])
CACHE_DIR =     pathlib.Path(os.environ['PULSAR_CACHE_DIR'])
STATE_DIR =     pathlib.Path(os.environ['PULSAR_STATE_DIR'])
VENV_DIR =      pathlib.Path(os.environ['PULSAR_VENV_DIR'])

LIBRARY_PATH = SRC_DIR / 'pulsar/library'

class Codex(typer.core.TyperGroup):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.book_shelf = dict[str, str]()

        # Add lazy commands for all spell books
        for spell_book_dir in LIBRARY_PATH.iterdir():

            book_title = spell_book_dir.stem

            if book_title.startswith('_'):
                continue

            if spell_book_dir.is_dir() \
            and not (spell_book_dir / '__init__.py').exists():
                continue

            self.book_shelf[book_title] = f'pulsar.library.{book_title}'

    def resolve_command(self, ctx, args):
        name = args[0] if args else None
        
        if name not in self.book_shelf:
            return super().resolve_command(ctx, args)
        
        import importlib
        module_name = self.book_shelf[name]
        importlib.import_module(module_name)
        spell_book = SpellBook.registry[module_name]
        cmd = typer.main.get_group(spell_book.app)
        cmd.name = name
        return name, cmd, args[1:]

    @staticmethod
    def main_callback(
        ctx: typer.Context,
        display_banner: bool = typer.Option(True, '--banner/--no-banner', help="Show ASCII banner."),
    ):
        if ctx.invoked_subcommand is None:
            if display_banner:
                stderr.print(ASCII_ART, style='bold blue', markup=False, highlight=False)
                stderr.print(
                    "By Andrew Ashby\n",
                    style='dim blue'
                )

            stderr.print("[bold]Usage:[/bold] pulsar [COMMAND] [OPTIONS]\n")
            stderr.print("Run [cyan]pulsar --help[/cyan] for more information.\n")

    @staticmethod
    def process_result(result, **kwargs):
        if result is not None:
            stdout.print(result)

app = typer.Typer(
    name='pulsar',
    cls=Codex,
    help="Pulsar - Arcane Package Manager",
    rich_markup_mode='rich',
    callback=Codex.main_callback,
    invoke_without_command=True,
    result_callback=Codex.process_result,
    pretty_exceptions_show_locals=True,
)

@app.command()
def version() -> str:
    """
    Display pulsar version
    """

    import tomllib

    pyproject_path = ROOT_DIR / 'pyproject.toml'
    assert pyproject_path.exists()

    with open(pyproject_path, 'rb') as f:
        data = tomllib.load(f)

    version_str = data.get('project', {}).get('version', 'unknown')
    return f'pulsar {version_str}'

@app.command(
    context_settings={
        "allow_extra_args": True, 
        "ignore_unknown_options": True,
    }, 
    add_help_option=False,
)
def uv(ctx: typer.Context):
    """
    Shortcut to the pulsar project environment
    """
    import subprocess

    subprocess.run(['__psr_uv_wrapper'] + ctx.args)

@app.command()
def clean(
    cache:  bool = typer.Option(False, '--cache', '-c', 
            help = "Clean [bold].cache/[/bold] and [bold]__pycache__/[/bold]"),
    state:  bool = typer.Option(False, '--state', '-s', help="Clean [bold].state/"),
    venv:   bool = typer.Option(False, '--venv', '-v',  help="Clean [bold].venv/"),
    bin:    bool = typer.Option(False, '--bin', '-b',   help="Clean [bold]bin/"),
    data:   bool = typer.Option(False, '--data', '-d',  help="Clean [bold]data/"),
    all:    bool = typer.Option(False, '--all', '-a',   help="Clean all environment directories."),
    yes:    bool = typer.Option(False, '--yes', '-y',   help="Skip confirmation."),
):
    """
    Clean pulsar environment directories
    """
    # TODO: Add safety checks to make sure that no critical files are deleted

    items_to_remove = set[pathlib.Path]()

    if cache or all:
        for item in CACHE_DIR.iterdir():
            items_to_remove.add(item)
        for pycache_dir in SRC_DIR.rglob('__pycache__'):
            items_to_remove.add(pycache_dir)

    if state or all:
        for item in STATE_DIR.iterdir():
            items_to_remove.add(item)

    if bin or all:
        for item in BIN_DIR.iterdir():
            items_to_remove.add(item)

    if venv or all and VENV_DIR.exists():
        items_to_remove.add(VENV_DIR)

    if data or all:
        for item in DATA_DIR.iterdir():
            items_to_remove.add(item)

    if len(items_to_remove) == 0:
        stderr.print("Nothing to delete.")
        return

    if not yes:
        stderr.print(f"\n[bold yellow]⚠ WARNING:[/bold yellow] This will delete the following directories:")
        for item in items_to_remove:
            stderr.print(item)

        if not typer.confirm("Are you sure you want to continue?"):
            stderr.print("[dim]Cancelled[/dim]\n")
            return

    stderr.print("[bold cyan]Cleaning directories...[/bold cyan]")

    import shutil
    for item in items_to_remove:
        shutil.rmtree(item)

    stderr.print("[bold green]Clean complete.[/bold green]\n")


if __name__ == '__main__':
    app()