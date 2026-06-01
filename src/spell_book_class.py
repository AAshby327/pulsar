import typing
import logging
import inspect
import pathlib

import typer
import rich.traceback

import pulsar_console
import pulsar_env

_DECORATOR_INPUT = typing.TypeVar("_DECORATOR_INPUT", bound=typing.Callable)
_TyperCommandDec = typing.Callable[[_DECORATOR_INPUT], _DECORATOR_INPUT]
_P = typing.ParamSpec("_P")
_R = typing.TypeVar("_R")

class Spell(typing.Generic[_P, _R]):

    func: typing.Callable[_P, _R] | None
    typer_command: _TyperCommandDec | None
    require_no_args: bool

    @staticmethod
    def _no_required_args(func: typing.Callable) -> bool:
        """Check if a callable has any required arguments (parameters without defaults)."""
        sig = inspect.signature(func)
        for param in sig.parameters.values():
            # Check if parameter has no default value and is not *args or **kwargs
            if (param.default is inspect.Parameter.empty and
                param.kind not in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD
                )):

                return False
        return True

    def __init__(
        self,
        typer_command: _TyperCommandDec = None,
        require_no_args: bool = True,
    ):
        self.func = None
        self.typer_command = typer_command
        self.require_no_args = require_no_args

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:

        if self.func is None:
            return None
        
        return self.func(*args, **kwargs)
    
    def define(self) -> _TyperCommandDec: 

        def decorator(func):
            self.func = func
            if self.typer_command is not None:

                def wrapper(*args, **kwargs):
                    if self.func is None:
                        return None
                    result = self.func(*args, **kwargs)
                    if result is not None:
                        pulsar_console.console.print(result)
                    return result

                wrapper.__signature__ = inspect.signature(func)
                self.typer_command(wrapper)
            return func
        
        return decorator
    
    def is_defined(self) -> bool:
        return self.func is not None

class SpellBook:

    BROKEN: type['BrokenSpellBook'] = None

    name: str
    script: pathlib.Path

    logger: logging.Logger

    dependencies: list[typing.Union['SpellBook', str]]

    install: Spell
    uninstall: Spell
    on_activate: Spell

    installed_with_system: Spell[[], bool]
    installed_with_pulsar: Spell[[], bool]
    version: Spell[[], str]

    typer_app: typer.Typer

    cache_dir: pathlib.Path

    def __init__(
        self, 
        name: str, 
        help: str | None = None,
        dependencies: list[typing.Union['SpellBook', str]] | None = None,
    ):
        self.name = name
        caller_frame = inspect.stack()[1]
        self.script = pathlib.Path(caller_frame.filename)
        caller_module_name = caller_frame.frame.f_globals['__name__']
        self.logger = logging.getLogger(caller_module_name)

        if help is None: 
            help = caller_frame.frame.f_globals.get('__doc__', '')

        self.dependencies = dependencies if dependencies is not None else []

        self.typer_app = typer.Typer(
            name=self.name,
            help=help,
        )

        self.install = Spell(self.typer_app.command('install'))
        self.uninstall = Spell(self.typer_app.command('uninstall'))
        self.on_activate = Spell()

        self.installed_with_system = Spell()
        self.installed_with_pulsar = Spell()
        self.version = Spell(self.typer_app.command('version'))

        self.cache_dir = pulsar_env.PULSAR_CACHE_DIR / self.name

        import library

        library.catalog[self.name] = self

    def __repr__(self):
        return f"<SpellBooK: {self.name}>"

    def is_installed(self) -> bool:
        return self.installed_with_pulsar() \
        or self.installed_with_system()

class BrokenSpellBook(SpellBook):
    
    def __init__(self, name: str, exception: Exception, traceback: rich.traceback.Traceback):
        super().__init__(name, f"[red]Broken: {exception}[/red]")
        self.traceback = traceback
        self.typer_app.callback(invoke_without_command=True)(self.print_error)

    def print_error(self):
        pulsar_console.err_console.print(self.traceback)

SpellBook.BROKEN = BrokenSpellBook
