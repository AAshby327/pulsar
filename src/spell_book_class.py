import typing
import logging
import inspect

import typer
import rich.traceback

import pulsar_console

_DECORATOR_INPUT = typing.TypeVar("_DECORATOR_INPUT", bound=typing.Callable)

class SpellBook:

    name: str
    script: str

    logger: logging.Logger

    dependencies: list[typing.Union['SpellBook', str]]

    _installer_spell: typing.Callable
    _uninstaller_spell: typing.Callable
    _on_activate_spell: typing.Callable

    typer_app: typer.Typer

    def __init__(
        self, 
        name: str, 
        help: str | None = None,
        dependencies: list[typing.Union['SpellBook', str]] | None = None,
    ):
        self.name = name
        caller_frame = inspect.stack()[1]
        self.script = caller_frame.filename
        caller_module_name = caller_frame.frame.f_globals['__name__']
        self.logger = logging.getLogger(caller_module_name)

        if help is None: 
            help = caller_frame.frame.f_globals.get('__doc__', '')

        self.dependencies = dependencies if dependencies is not None else []

        self.typer_app = typer.Typer(
            name=self.name, 
            help=help,
        )

        self._installer_spell = None
        self._uninstaller_spell = None
        self._on_activate_spell = None

        import library

        library.catalog[self.name] = self

    def __repr__(self):
        return f"<SpellBooK: {self.name}>"

    def installer(self, func: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
        assert not _has_required_args(func)
        self._installer_spell = func
        self.typer_app.command('install')(func)
        return func
    
    def uninstaller(self, func: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
        assert not _has_required_args(func)
        self._uninstaller_spell = func
        self.typer_app.command('uninstall')(func)
        return func
    
    def on_activate(self, func: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
        assert not _has_required_args(func)
        self._on_activate_spell = func
        return func

class BrokenSpellBook(SpellBook):
    
    def __init__(self, name: str, exception: Exception, traceback: rich.traceback.Traceback):
        super().__init__(name, f"[red]Broken: {exception}[/red]")
        self.traceback = traceback
        self.typer_app.callback(invoke_without_command=True)(self.print_error)

    def print_error(self):
        pulsar_console.err_console.print(self.traceback)

def _has_required_args(func: typing.Callable) -> bool:
    """Check if a callable has any required arguments (parameters without defaults)."""
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        # Check if parameter has no default value and is not *args or **kwargs
        if (param.default is inspect.Parameter.empty and
            param.kind not in (
                inspect.Parameter.VAR_POSITIONAL, 
                inspect.Parameter.VAR_KEYWORD
            )):

            return True
    return False