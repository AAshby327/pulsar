import sys

import typer

from pulsar.summoning_circle import Installer

class SpellBook:

    registry = dict[str, 'SpellBook']()

    name: str
    app: typer.Typer
    installer: Installer | None

    def __init__(
            self, 
            name: str,
            help_text: str | None = None,

            invoke_without_command: bool = False,
            no_args_is_help: bool = False,
        ):

        self.name = name
        self.app = typer.Typer(
            name=name,
            rich_markup_mode='rich',
        )

        assert name not in SpellBook.registry
        SpellBook.registry[name] = self

        if name in sys.modules:
            module = sys.modules[name]
            help_text = module.__doc__

        self.name = name
        self.app = typer.Typer(
            name=name,
            help=help_text,
            rich_markup_mode='rich',
            invoke_without_command=invoke_without_command,
            no_args_is_help=no_args_is_help,
        )

        self.installer = None
