import os
import sys
import abc
import typing
import types
import ast
import inspect
import dataclasses

if typing.TYPE_CHECKING:
    from rich.console import Console


SEPARATOR = '-'
KEYWORD_OPERATOR = '--'

_NULL_VAL = '__NULL__'

_PARSER_TYPE = typing.TypeVar('_PARSER_TYPE')

class Parser(abc.ABC, typing.Generic[_PARSER_TYPE]):
    @abc.abstractmethod
    def __call__(self, *args: str) -> _PARSER_TYPE: ...

class DefaultParser(Parser):
    def __call__(self, *args: str):
        return ' '.join(args) # TODO: Implement based on fire ast parser

@dataclasses.dataclass
class Arg:
    aliases: list[str] = dataclasses.field(default_factory=list)
    env_var: str | None = None

    default: typing.Any | typing.Callable[[], typing.Any] = _NULL_VAL

    parser: Parser = dataclasses.field(default_factory=DefaultParser)

    add_help_option: bool = True
    hidden: bool = False
    help: str | None = None
    help_section: str | None = None

    positional: bool = dataclasses.field(init=False, default=True)
    keyword: bool = dataclasses.field(init=False, default=True)

    def get_default(self):
        if callable(self.default):
            return self.default()
        return self.default
    
    def sync(self, param: inspect.Parameter):

        if param.name not in self.aliases:
            self.aliases.insert(0, param.name)

        if self.default is _NULL_VAL and param.default is not inspect._empty:
            self.default = param.default
        
        self.positional = param.kind in \
            (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.keyword = param.kind in \
            (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)

@dataclasses.dataclass
class Spell:
    name: str | None = None

    call: typing.Callable | None = None
    print_result: bool = False
    call_result: bool = False

    rich_console: Console | None = None
    rich_error_console: Console | None = None

    add_help_option: bool = True
    hidden: bool = False
    help: str | None = None
    help_epilog: str | None = None
    help_section: str | None = None
    deprecated: bool = False

    args: dict[str, Arg] = None
    subcommands: dict[str, Spell] = None

    def __post_init__(self):

        if self.args is None:
            self.args = {}
        if self.subcommands is None:
            self.subcommands = {}

    @classmethod
    def define(
        cls,
        name: str | None = None,
        print_result: bool = False,
        call_result: bool = False,
        rich_console: Console | None = None,
        rich_error_console: Console | None = None,
        add_help_option: bool = True,
        hidden: bool = False,
        help: str | None = None,
        help_epilog: str | None = None,
        help_section: str | None = None,
        deprecated: bool = False,
    ) -> typing.Callable[[typing.Callable], Spell]:
        
        def decorator(func: typing.Callable) -> Spell:
            assert inspect.isfunction(func)
            signature = inspect.signature(func)
            args: dict[str, Arg] = {}

            for param_name, param in signature.parameters.items():
                if isinstance(param.default, Arg):
                    args[param_name] = param.default
                else:
                    args[param_name] = Arg()
                args[param_name].sync(param)

            spell_name = name if name is not None else func.__name__
            return Spell(
                name=spell_name,
                call=func,
                print_result=print_result,
                call_result=call_result,
                rich_console=rich_console,
                rich_error_console=rich_error_console,
                add_help_option=add_help_option,
                hidden=hidden,
                help=help,
                help_epilog=help_epilog,
                help_section=help_section,
                deprecated=deprecated,
                args=args,
            )
        
        return decorator

    
    def parse_args(self, *args: str) -> tuple[list, dict[str, typing.Any]]:
        
        str_args: str = []
        str_kwargs: dict[str, list[str]] = {}

        current_kw: str | None = None

        for arg in args:

            if arg.startswith(KEYWORD_OPERATOR):
                current_kw = arg[len(KEYWORD_OPERATOR):].strip()
                str_kwargs[current_kw] = []
                continue

            if current_kw is None:
                str_args.append(arg)
            else:
                str_kwargs[current_kw].append(arg)
        
        for key in str_kwargs:
            if key not in self.args:
                raise TypeError(f"{self.name}() got an unexpected keyword argument '{key}'")
            
            if not self.args[key].keyword:
                raise TypeError(f"{self.name}() got a positional-only argument passed as a keyword argument: '{key}'")

        parsed_args = []
        parsed_kwargs = {}

        for i, arg_name in enumerate(self.args):

            arg = self.args[arg_name]

            if i < len(str_args):
                parsed_args.append(arg.parser(str_args[i]))
            elif arg_name in str_kwargs:
                parsed_kwargs[arg_name] = arg.parser(*str_kwargs[arg_name])
            else:
                default = arg.get_default()

                if default is _NULL_VAL:
                    raise TypeError(f"{self.name}() missing required argument: '{arg_name}'")

                if not arg.keyword:
                    parsed_args.append(default)
                else:
                    parsed_kwargs[arg_name] = default

        return parsed_args, parsed_kwargs

    def invoke(self, *args: str):
        
        if len(args) > 0 and args[0] in self.subcommands:
            return self.subcommands[args[0]].invoke(args[1:])
        
        parsed_args, parsed_kwargs = self.parse_args(*args)

        return self.__call__(*parsed_args, **parsed_kwargs)
    
    def run_cli(self):
        return self.invoke(sys.argv[1:])

    def __call__(self, *args, **kwds):

        if self.call is None:
            raise RuntimeError(f"Spell '{self.name}' call not set.")

        result = self.call(*args, **kwds)

        if self.print_result:
            if self.rich_console is not None:
                self.rich_console.print(result)
            else: 
                print(result)

        return result

            
if __name__ == '__main__':
    args = sys.argv[1:]

    @Spell.define(print_result=True)
    def test_callable(arg, arg4):
        return str(arg) + '!' + str(arg4)
    
    test_callable.invoke(*args)