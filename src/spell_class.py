import sys
import typing

if typing.TYPE_CHECKING:
    from rich.console import Console

_DECORATOR_INPUT = typing.TypeVar('_DECORATOR_INPUT')

def parse_args(argv: list[str]) -> tuple[tuple, dict[str, typing.Any]]:
    args = list()
    kwargs = dict()
    current_key: str | None = None

    for arg in argv:
        if arg.startswith('--'):
            if current_key is not None:
                kwargs[current_key] = True
            current_key = arg[2:]
        else:
            try: arg = eval(arg)
            except: pass
            if current_key is not None:
                kwargs[current_key] = arg
                current_key = None
            else:
                args.append(arg)

    if current_key is not None:
        kwargs[current_key] = True
    return tuple(args), kwargs


class Spell:

    name: str
    hidden: bool
    deprecated: bool
    
    help: str | None
    help_section: str | None
    add_help_option: bool
    no_args_is_help: bool

    print_result: bool
    rich_console: Console | None = None
    rich_err_console: Console | None = None

    call: typing.Callable[..., typing.Any] | None
    sub_commands: dict[str, 'Spell']

    def __init__(
        self,

        name: str,
        hidden: bool = False,
        deprecated: bool = False,

        help: str | None = None,
        help_section: str | None = None,
        add_help_option: bool = True,
        no_args_is_help: bool = False,

        print_result: bool = True,
        rich_console: Console | None = None,
        rich_err_console: Console | None = None,

        call: typing.Callable[..., typing.Any] | None = None,
    ):
        self.name = name
        self.hidden = hidden
        self.deprecated = deprecated

        self.help = help
        self.help_section = help_section
        self.add_help_option = add_help_option
        self.no_args_is_help = no_args_is_help

        self.print_result = print_result
        self.rich_console = rich_console
        self.rich_err_console = rich_err_console

        self.call = call
        self.sub_commands = dict()


    def __call__(self, *args, **kwargs) -> typing.Any:

        if isinstance(args[0], str) and args[0] in self.sub_commands:
            return self.sub_commands[args[0]](*args[1:], **kwargs)
        
        if self.call is None:
            raise NotImplementedError()
        
        result = self.call(*args, **kwargs)
        if self.print_result:
            if self.rich_console is not None:
                self.rich_console.print(result)
            else: print(result)
        return result
    

    def run_cli(self):
        args, kwargs = parse_args(sys.argv[1:])
        return self.__call__(*args, **kwargs)

    
    def command(
        self, 

        name: str | None = None,
        hidden: bool = False,
        deprecated: bool = False,

        help: str | None = None,
        help_section: str | None = None,
        add_help_option: bool = True,
        no_args_is_help: bool = False,

        print_result: bool = True,
        rich_console: Console | None = '__NULL__',
        rich_err_console: Console | None = '__NULL__',

    ) -> typing.Callable[[_DECORATOR_INPUT], _DECORATOR_INPUT]:
        
        def decorator(f: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
            import inspect
            if inspect.isfunction(f):

                cmd_name = name if name is not None else f.__name__

                child_console = self.rich_console \
                    if rich_console == '__NULL__' else rich_console
                child_err_console = self.rich_err_console \
                    if rich_err_console == '__NULL__' else rich_err_console

                assert cmd_name not in self.sub_commands

                self.sub_commands[cmd_name] = Spell(
                    name=cmd_name,
                    hidden=hidden,
                    deprecated=deprecated,
                    help=help,
                    help_section=help_section,
                    add_help_option=add_help_option,
                    no_args_is_help=no_args_is_help,
                    print_result=print_result,
                    rich_console=child_console,
                    rich_err_console=child_err_console,
                    call=f,
                )

            raise TypeError(f"Spell.command not supported for type: {f}")
        
        return decorator

