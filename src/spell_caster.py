
__version__ = '0.2.0'


import sys
import typing
import dataclasses
import inspect
import ast
import abc
import collections.abc
import types
import pathlib

try: 
    import rich
    import rich.console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


SEPARATOR = '-'
KEYWORD_OPERATOR = '--'

_NULL_VAL = '__NULL__'
_PARSER_TYPE = typing.TypeVar("_PARSER_TYPE")
_DECORATOR_INPUT = typing.TypeVar("_DECORATOR_INPUT")

spell_registry = dict[int, 'Spell']()

output_console: rich.console.Console | None = None
error_console: rich.console.Console | None = None
if RICH_AVAILABLE:
    output_console = rich.console.Console()
    error_console = rich.console.Console(stderr=True)

_unused_sys_argv = sys.argv[1:]

class SpellError(Exception): ...

class Parser(typing.Generic[_PARSER_TYPE]):
    # Default parsing logic from fire.parser.DefaultParseValue
    def __call__(self, *argv: str) -> _PARSER_TYPE:

        assert len(argv) > 0
        value = argv[0]
        # Maybe later add support for multiple args

        root = ast.parse(value, mode='eval')
        if isinstance(root.body, ast.BinOp):
            raise ValueError(value)

        def replacement(node):
            value = node.id
            # These are the only builtin constants supported by literal_eval.
            if value in ('True', 'False', 'None'):
                return node
            return ast.Constant(value)
        
        for node in ast.walk(root):
            for field, child in ast.iter_fields(node):
                if isinstance(child, list):
                    for index, subchild in enumerate(child):
                        if isinstance(subchild, ast.Name):
                            child[index] = replacement(subchild)
            
                elif isinstance(child, ast.Name):
                    rep = replacement(child)
                    setattr(node, field, rep)
        
        return ast.literal_eval(root)


@dataclasses.dataclass(frozen=True, slots=True)
class Arg:
    name: str | None = None # If None, this arg is positional only

    parser: Parser = dataclasses.field(default_factory=Parser)
    default: typing.Any = _NULL_VAL
    flag_val: typing.Any = True

    kwrd_only: bool = False

    def __post_init__(self):
        if self.name is None and self.kwrd_only:
            raise ValueError("Keyword arguments must have a name.")

    def get_default_val(self):
        return self.default

    def get_flag_val(self):
        return self.flag_val

class ResultHandler(abc.ABC):
    @abc.abstractmethod
    def __call__(self, result, *remaining_argv: str): ...

@dataclasses.dataclass
## TODO: Make not dataclass and add lazy loading
class Spell:

    source: typing.Callable = _NULL_VAL
    subcommands: dict[str] = dataclasses.field(
        default_factory=dict,
    )

    result_handler: ResultHandler = None

    args: list[Arg] = dataclasses.field(
        default_factory=list, 
        init=False,
    )

    pos_args: list[Arg] = dataclasses.field(
        default_factory=list, 
        init=False,
    )
    kw_args: dict[str, Arg] = dataclasses.field(
        default_factory=dict, 
        init=False,
    )


    def define(self, source: _DECORATOR_INPUT) -> _DECORATOR_INPUT:

        source_id = id(source)
        if source_id in spell_registry:
            raise SpellError(f"Can not define multiple spells on {source}")
        spell_registry[source_id] = self
        self.source = source

        is_callable = callable(self.source)

        # Get subcommands
        if isinstance(self.source, collections.abc.Sequence):
            for i, val in enumerate(self.source):
                self.subcommands[str(i)] = val

        if isinstance(self.source, collections.abc.Mapping):
            for key, val in self.source.items():
                if key in self.subcommands:
                    raise KeyError(f"Dictionary key subcommand shadows sequence index: {key}")
                # assert key not in self.subcommands
                self.subcommands[str(key)] = val

        entries = set(getattr(self.source, '__dict__', dict()))
        entries.update(getattr(self.source, '__slots__', tuple()))

        source_type = type(self.source)

        for attr in dir(self.source):
            val = getattr(self.source, attr)

            if attr not in entries:

                # Skip class vars
                if getattr(source_type, attr, _NULL_VAL) is val:
                    continue

                # Skip class methods
                if is_callable:
                    method_self = getattr(val, '__self__', self.source) 
                    if method_self is not self.source:
                        continue

            # assert attr not in self.subcommands
            if attr in self.subcommands:
                raise KeyError(f"Attribute shadows dictionary key subcommand: {attr}")
            self.subcommands[attr] = val

        # Get args
        if is_callable:
            signature = inspect.signature(self.source)
            
            for param in signature.parameters.values():
                arg_name = param.name if param.kind not in(
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.VAR_POSITIONAL,
                ) else None

                default = _NULL_VAL if param.default == \
                inspect._empty else param.default

                arg = Arg(
                    name = arg_name,
                    default=default,
                    kwrd_only=param.kind==\
                        inspect.Parameter.KEYWORD_ONLY,
                )

                self.args.append(arg)

                if not arg.kwrd_only:
                    self.pos_args.append(arg)

                if arg.name is not None:
                    # assert arg.name not in self.kw_args
                    if arg.name in self.kw_args:
                        raise KeyError(f"Duplicate argument names: {arg.name}")
                    self.kw_args[arg.name] = arg
            
        return source

    @classmethod
    def get_spell(cls, source) -> Spell:
        if isinstance(source, Spell):
            return source

        source_id = id(source)
        if source_id in spell_registry:
            return spell_registry[source_id]

        new_spell = cls()
        new_spell.define(source)
        return new_spell

    def parse_argv(self, *argv: str) -> tuple[list, dict[str], list[str]]:
        parsed_args = list()
        parsed_kwargs = dict[str]()

        remaining_args = set(self.args)
        current_arg: Arg | None = None
        current_kwargv = list[str]()
        pos_arg_index = 0

        def flush_kwargv():
            nonlocal parsed_kwargs
            nonlocal remaining_args
            nonlocal current_arg
            nonlocal current_kwargv

            if current_arg is None:
                return

            key = current_arg.name

            if len(current_kwargv) > 0:
                parsed_kwargs[key] = current_arg.parser(*current_kwargv)
            else:
                parsed_kwargs[key] = current_arg.get_flag_val()

            remaining_args.discard(current_arg)
            current_arg = None
            current_kwargv = list()

        arg_consumed_count = 0
        for arg in argv:
            arg_consumed_count += 1

            if arg == SEPARATOR:
                break

            if arg.startswith(KEYWORD_OPERATOR):
                flush_kwargv()

                key = arg[len(KEYWORD_OPERATOR):]
                if key in self.kw_args:
                    current_arg = self.kw_args[key]
                    # assert current_arg in remaining_args
                    if current_arg not in remaining_args:
                        TypeError(f"Spell got multiple values for argument '{current_arg.name}'")

                else:
                    # TODO: current_arg = self.var_kwargs
                    raise TypeError(f"Spell got an unexpected keyword argument '{key}'")

                continue

            if current_arg is not None:
                current_kwargv.append(arg)
                continue

            if pos_arg_index < len(self.pos_args):
                pos_arg = self.pos_args[pos_arg_index]
                # assert pos_arg in remaining_args
                if pos_arg not in remaining_args:
                    TypeError(f"Spell got multiple values for argument '{current_arg.name}'")
            else:
                # TODO: pos_arg = self.var_args
                # raise AttributeError()
                raise TypeError(f"Spell takes at most {len(self.pos_args)} but more were given.")

            parsed_args.append(pos_arg.parser(arg))
            remaining_args.discard(pos_arg)
            pos_arg_index += 1

        flush_kwargv()
        unused_argv = list(argv[arg_consumed_count:])

        for arg in remaining_args:
            # TODO: Handle env vars

            if arg.default is _NULL_VAL:
                if arg.name is None:
                    raise TypeError(f"Spell missing required positional arg of index: {self.pos_args.index(arg)}")
                else:
                    raise TypeError(f"Spell missing required arg: '{arg.name}'")
            val = arg.get_default_val()

            if arg.name is None:
                parsed_args.append(val)
            else:
                parsed_kwargs[arg.name] = val

        return parsed_args, parsed_kwargs, unused_argv

    def __call__(self, *args, **kwargs):

        if not callable(self.source):
            raise SpellError(f"Spell is not ")

        return self.source(*args, **kwargs)

    def __fire__(source, *argv: str):

        if len(argv) == 0 and not callable(source):
            return source

        spell = Spell.get_spell(source)

        if len(argv) > 0 and argv[0] in spell.subcommands:
            result = spell.subcommands[argv[0]]
            rem_argv = argv[1:]
        else:
            args, kwargs, rem_argv = spell.parse_argv(*argv)
            result = spell.__call__(*args, **kwargs)

        return Spell.__fire__(result, *rem_argv)


    def Fire(source, *argv: str) -> typing.Any:
        global _unused_sys_argv
        global output_console

        if len(argv) == 0 and len(_unused_sys_argv) > 0:
            argv = _unused_sys_argv
            _unused_sys_argv = list()

        if error_console is not None:
            try:
                result = Spell.__fire__(source, *argv)
            except Exception:
                # TODO: Add user friendly error messages so simple 
                # cli mistakes are not long tracebacks
                error_console.print_exception()
                return None
        else:
            result = Spell.__fire__(source, *argv)

        if output_console is not None:
            output_console.print(result)
        else:
            print(result)

        return result















# if __name__ == '__main__':
#     @Spell().define
#     def test(a: int, b: float = 0.0, c = 'a') -> str:
#         return ", ".join([str(a), str(b), str(c)])

#     Spell.Fire(test)




def function_test(a: int, b: float = 0.0, c = 'a') -> str:
    return ", ".join([str(a), str(b), str(c)])

class class_test:

    a: int

    class_var = 0

    def __init__(self, a: int, b: float = 0.0, c = 'a'):
        self.a = a
        self.b = b
        self.c = c

    @classmethod
    def class_method_test(cls, a: int, b: float = 0.0, c = 'a') -> str:
        return ", ".join([str(cls), str(a), str(b), str(c)])

    @staticmethod
    def static_method_test(a: int, b: float = 0.0, c = 'a') -> str:
        return ", ".join([str(a), str(b), str(c)])

    def instance_method_test(self, a: int, b: float = 0.0, c = 'a') -> str:
        return ", ".join([str(self), str(a), str(b), str(c)])

    # def __call__(self, *args, **kwds):
    #     return args, kwds

dict_test = {
    'a': 1,
    'test': function_test,
}

sequence_test = [
    2,
    3.0,
    "Hello",
    class_test,
]

instance_test = class_test(9)

import test_module

import dataclasses

@dataclasses.dataclass
class dataclass_test:
    a: int
    b: float = 0.0
    c: dict = dataclasses.field(default_factory=dict)

    class_var: typing.ClassVar[int] = 0

dataclass_inst_test = dataclass_test(0)


import time
test_start = time.time()


Spell.Fire([
    function_test, 
    class_test,
    class_test.class_method_test,
    class_test.static_method_test,
    dict_test,
    sequence_test,
    instance_test,
    test_module,
    dataclass_test,
    dataclass_inst_test
])






###### v1 ########
# import os
# import sys
# import abc
# import typing
# import types
# import ast
# import inspect
# import dataclasses

# if typing.TYPE_CHECKING:
#     from rich.console import Console

# SEPARATOR = '-'
# FLAG_OPERATOR = '-'
# KEYWORD_OPERATOR = '--'
# ARG_REGISTRY_ATTR_NAME = '__SPELL_ARGS__'
# SPELL_ATTR_NAME = '__SPELL__'

# _NULL_VAL = '__NULL__'
# _PARSER_TYPE = typing.TypeVar("_PARSER_TYPE")
# _DECORATOR_INPUT = typing.TypeVar("_DECORATOR_INPUT")

# class Parser(abc.ABC, typing.Generic[_PARSER_TYPE]):
#     @abc.abstractmethod
#     def __call__(self, *args: str) -> _PARSER_TYPE: ...

# class DefaultParser(Parser):
#     def __call__(self, *args: str):
#         return ' '.join(args) # TODO: Implement based on fire ast parser

# @dataclasses.dataclass
# class Arg:
#     name: str | None = None
#     aliases: list[str] = dataclasses.field(default_factory=list)
#     env_var: str | None = None
#     flag_char: str | None = None
    
#     parser: Parser = dataclasses.field(default_factory=DefaultParser)
#     default: typing.Any | typing.Callable[[], typing.Any] = _NULL_VAL
#     flag_val: typing.Any | typing.Callable[[], typing.Any] = True
    
#     hidden: bool = False
#     help: str | None = None
#     help_section: str | None = None
#     add_help_option: bool = True

#     kwrd_only: bool = False
    
#     def __post_init__(self):
#         if self.kwrd_only: assert self.name is not None
#         if self.flag_char is not None:
#             assert len(self.flag_char) == 1

#     def __call__(self, spell: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         if not hasattr(spell, ARG_REGISTRY_ATTR_NAME):
#             setattr(spell, ARG_REGISTRY_ATTR_NAME, _ArgRegistry())
        
#         registry: _ArgRegistry = getattr(spell, ARG_REGISTRY_ATTR_NAME)
#         registry.add(self)

# @dataclasses.dataclass
# class VarArgs:
#     parser: Parser = dataclasses.field(default_factory=DefaultParser)
    
#     hidden: bool = False
#     help: str | None = None
#     help_section: str | None = None
#     add_help_option: bool = True

#     def __call__(self, spell: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         if not hasattr(spell, ARG_REGISTRY_ATTR_NAME):
#             setattr(spell, ARG_REGISTRY_ATTR_NAME, _ArgRegistry())
        
#         registry: _ArgRegistry = getattr(spell, ARG_REGISTRY_ATTR_NAME)
#         registry.add(self)

# @dataclasses.dataclass
# class VarKwargs:
#     parser: Parser = dataclasses.field(default_factory=DefaultParser)
#     flag_val: typing.Any | typing.Callable[[], typing.Any] = True
    
#     hidden: bool = False
#     help: str | None = None
#     help_section: str | None = None
#     add_help_option: bool = True

#     def __call__(self, spell: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         if not hasattr(spell, ARG_REGISTRY_ATTR_NAME):
#             setattr(spell, ARG_REGISTRY_ATTR_NAME, _ArgRegistry())
        
#         registry: _ArgRegistry = getattr(spell, ARG_REGISTRY_ATTR_NAME)
#         registry.add(self)

# class _ArgRegistry:
#     def __init__(self):
#         self.pos_args = list[Arg]()
#         self.kw_args = dict[str, Arg]()
#         self.env_args = dict[str, Arg]()
#         self.flag_args = dict[str, Arg]()

#         self.var_args: VarArgs | None = None
#         self.var_kwargs: VarKwargs | None = None

#         self.all_args = set[Arg]()

#     def add(self, arg: Arg):

#         if isinstance(arg, VarArgs):
#             assert self.var_args is None
#             self.var_args = arg
#             return
        
#         if isinstance(arg, VarKwargs):
#             assert self.var_kwargs is None
#             self.var_kwargs = arg
#             return
        
#         assert arg not in self.all_args
#         self.all_args.add(arg)
        
#         if not arg.kwrd_only:
#             self.pos_args.append(arg)
        
#         if arg.name is not None:
#             assert arg.name not in self.kw_args
#             self.kw_args[arg.name] = arg

#         if arg.env_var is not None:
#             assert arg.env_var not in self.env_args
#             self.env_args[arg.env_var] = arg

#         if arg.flag_char is not None:
#             assert arg.flag_char not in self.flag_args
#             self.flag_args[arg.flag_char] = arg

#         for key in arg.aliases:
#             assert key not in self.kw_args
#             self.kw_args[key] = arg

#     def parse(self, *argv: str) -> tuple[list, dict[str]]:

#         ## TODO: Need to account for default vals
#         ## TODO: Add support for flags and ENV VARS

#         str_args = list[str]()
#         str_kwargs = dict[str, list[str]]()
#         current_kw = str | None = None

#         for arg in argv:
#             if arg.startswith(KEYWORD_OPERATOR):
#                 current_kw = arg[len(KEYWORD_OPERATOR):].strip()
#                 str_kwargs[current_kw] = []
#                 continue

#             if current_kw is None:
#                 str_args.append(arg)
#             else:
#                 str_kwargs[current_kw].append(arg)

#         args = list()
#         kwargs = dict[str]()
#         used_args = set[Arg]()
#         pos_arg_count = len(self.pos_args)

#         assert self.var_args is not None or len(str_args) <= pos_arg_count

#         for i, arg in enumerate(str_args):
#             if i < pos_arg_count:
#                 args.append(self.pos_args[i].parser(arg))
#                 used_args.add(self.pos_args[i])
#             else:
#                 args.append(self.var_args.parser(arg))

#         for key, arg_list in str_kwargs.items():
#             if key in self.kw_args:
#                 assert self.kw_args[key] not in used_args
#                 kwargs[key] = self.kw_args[key].parser(*arg_list)
#                 used_args.add(self.kw_args[key])

#             else:
#                 assert self.var_kwargs is not None
#                 kwargs[key] = self.var_kwargs.parser(*arg_list)

#         return args, kwargs


# @dataclasses.dataclass
# class Spell:
#     name: str | None = None

#     call: typing.Callable | None = None
#     print_result: bool = False
#     call_result: bool = False

#     rich_console: Console | None = None
#     rich_error_console: Console | None = None

#     hidden: bool = False
#     help: str | None = None
#     help_epilog: str | None = None
#     help_section: str | None = None
#     deprecated: bool = False
#     add_help_option: bool = True

#     arg_registry: _ArgRegistry | None = dataclasses.field(init=False, default=None)
#     subcommands: dict[str, Spell] = dataclasses.field(default_factory=dict)

#     def __post_init__(self):
#         pass

#     def define(self, call: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         assert self.call is None
#         self.call = call
#         ## TODO: Get arg registry from call
#         return call

#     # @classmethod
#     # def define(
#     #     cls,
#     #     name: str | None = None,
#     #     print_result: bool = False,
#     #     call_result: bool = False,
#     #     rich_console: Console | None = None,
#     #     rich_error_console: Console | None = None,
#     #     add_help_option: bool = True,
#     #     hidden: bool = False,
#     #     help: str | None = None,
#     #     help_epilog: str | None = None,
#     #     help_section: str | None = None,
#     #     deprecated: bool = False,
#     # ) -> typing.Callable[[typing.Callable], Spell]:
        
#     #     def decorator(func: typing.Callable) -> Spell:
#     #         assert inspect.isfunction(func)
#     #         signature = inspect.signature(func)
#     #         args: dict[str, Arg] = {}

#     #         for param_name, param in signature.parameters.items():
#     #             if isinstance(param.default, Arg):
#     #                 args[param_name] = param.default
#     #             else:
#     #                 args[param_name] = Arg()
#     #             args[param_name].sync(param)

#     #         spell_name = name if name is not None else func.__name__
#     #         return Spell(
#     #             name=spell_name,
#     #             call=func,
#     #             print_result=print_result,
#     #             call_result=call_result,
#     #             rich_console=rich_console,
#     #             rich_error_console=rich_error_console,
#     #             add_help_option=add_help_option,
#     #             hidden=hidden,
#     #             help=help,
#     #             help_epilog=help_epilog,
#     #             help_section=help_section,
#     #             deprecated=deprecated,
#     #             args=args,
#     #         )
        
#     #     return decorator

    
#     def parse_args(self, *args: str) -> tuple[list, dict[str, typing.Any]]:
        
#         str_args: str = []
#         str_kwargs: dict[str, list[str]] = {}

#         current_kw: str | None = None

#         for arg in args:

#             if arg.startswith(KEYWORD_OPERATOR):
#                 current_kw = arg[len(KEYWORD_OPERATOR):].strip()
#                 str_kwargs[current_kw] = []
#                 continue

#             if current_kw is None:
#                 str_args.append(arg)
#             else:
#                 str_kwargs[current_kw].append(arg)
        
#         for key in str_kwargs:
#             if key not in self.args:
#                 raise TypeError(f"{self.name}() got an unexpected keyword argument '{key}'")
            
#             if not self.args[key].keyword:
#                 raise TypeError(f"{self.name}() got a positional-only argument passed as a keyword argument: '{key}'")

#         parsed_args = []
#         parsed_kwargs = {}

#         for i, arg_name in enumerate(self.args):

#             arg = self.args[arg_name]

#             if i < len(str_args):
#                 parsed_args.append(arg.parser(str_args[i]))
#             elif arg_name in str_kwargs:
#                 parsed_kwargs[arg_name] = arg.parser(*str_kwargs[arg_name])
#             else:
#                 default = arg.get_default()

#                 if default is _NULL_VAL:
#                     raise TypeError(f"{self.name}() missing required argument: '{arg_name}'")

#                 if not arg.keyword:
#                     parsed_args.append(default)
#                 else:
#                     parsed_kwargs[arg_name] = default

#         return parsed_args, parsed_kwargs

#     def invoke(self, *argv: str):
        
#         if len(argv) > 0 and argv[0] in self.subcommands:
#             return self.subcommands[argv[0]].invoke(argv[1:])
        
#         parsed_args, parsed_kwargs = self.parse_args(*argv)

#         return self.__call__(*parsed_args, **parsed_kwargs)
    
#     def run_cli(self):
#         return self.invoke(sys.argv[1:])

#     def __call__(self, *args, **kwds):

#         if self.call is None:
#             raise RuntimeError(f"Spell '{self.name}' call not set.")

#         result = self.call(*args, **kwds)

#         if self.print_result:
#             if self.rich_console is not None:
#                 self.rich_console.print(result)
#             else: 
#                 print(result)

#         return result

            
# # if __name__ == '__main__':
# #     args = sys.argv[1:]

# #     @Spell.define(print_result=True)
# #     def test_callable(arg, arg4):
# #         return str(arg) + '!' + str(arg4)
    
# #     test_callable.invoke(*args)







##### v2 ######
# import os
# import sys
# import abc
# import typing
# import types
# import ast
# import inspect
# import dataclasses

# if typing.TYPE_CHECKING:
#     from rich.console import Console

# SEPARATOR = '-'
# FLAG_OPERATOR = '-'
# KEYWORD_OPERATOR = '--'
# KEYWORD_ASSIGNMENT_OPERATOR = '='
# ARG_ATTR_NAME = '__SPELL_ARGS__'
# VAR_ARGS_ATTR_NAME = '__SPELL_VARGS__'
# VAR_KWARGS_ATTR_NAME = '__SPELL_KWARGS__'
# SPELL_ATTR_NAME = '__SPELL__'

# _NULL_VAL = '__NULL__'
# _PARSER_TYPE = typing.TypeVar("_PARSER_TYPE")
# _DECORATOR_INPUT = typing.TypeVar("_DECORATOR_INPUT")


# class ParserError(Exception): ...
# class DefaultFactoryError(Exception): ...

# class Parser(abc.ABC, typing.Generic[_PARSER_TYPE]):
#     @abc.abstractmethod
#     def __call__(self, *argv: str) -> _PARSER_TYPE: ...

# class DefaultParser(Parser):
#     def __call__(self, *argv: str):
#         return ' '.join(argv) # TODO: Implement based on fire ast parser


# @dataclasses.dataclass
# class Arg:
#     name: str | None = None
#     aliases: list[str] = dataclasses.field(default_factory=list)
#     env_var: str | None = None
#     flag_char: str | None = None
    
#     parser: Parser = dataclasses.field(default_factory=DefaultParser)
#     default: typing.Any | typing.Callable[[], typing.Any] = _NULL_VAL
#     flag_val: typing.Any | typing.Callable[[], typing.Any] = True
    
#     hidden: bool = False
#     help: str | None = None
#     help_section: str | None = None
#     add_help_option: bool = True

#     kwrd_only: bool = False
    
#     def __post_init__(self):
#         if self.kwrd_only: assert self.name is not None
#         if self.flag_char is not None:
#             assert len(self.flag_char) == 1

#     def __call__(self, func: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         spell = getattr(func, SPELL_ATTR_NAME, None)
#         if spell is None: spell = func

#         if isinstance(spell, Spell):
#             spell.add_arg(self)
#             return
        
#         args = getattr(func, ARG_ATTR_NAME, [])
#         args.append(self)
#         if not hasattr(func, ARG_ATTR_NAME):
#             setattr(func, ARG_ATTR_NAME, args)


# @dataclasses.dataclass
# class VarArgs:
#     parser: Parser = dataclasses.field(default_factory=DefaultParser)
    
#     hidden: bool = False
#     help: str | None = None
#     help_section: str | None = None
#     add_help_option: bool = True

#     def __call__(self, func: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         spell = getattr(func, SPELL_ATTR_NAME, None)
#         if spell is None: spell = func

#         if isinstance(spell, Spell):
#             spell.add_arg(self)
#             return
        
#         assert not hasattr(func, VAR_ARGS_ATTR_NAME)
#         setattr(func, VAR_ARGS_ATTR_NAME, self)
        

# @dataclasses.dataclass
# class VarKwargs:
#     parser: Parser = dataclasses.field(default_factory=DefaultParser)
#     flag_val: typing.Any | typing.Callable[[], typing.Any] = True
    
#     hidden: bool = False
#     help: str | None = None
#     help_section: str | None = None
#     add_help_option: bool = True

#     def __call__(self, func: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         spell = getattr(func, SPELL_ATTR_NAME, None)
#         if spell is None: spell = func

#         if isinstance(spell, Spell):
#             spell.add_arg(self)
#             return
        
#         assert not hasattr(func, VAR_KWARGS_ATTR_NAME)
#         setattr(func, VAR_KWARGS_ATTR_NAME, self)
        

# @dataclasses.dataclass
# class Spell:
#     name: str | None = None

#     func: typing.Callable | None = None
#     print_result: bool = True
#     call_result: bool = True

#     rich_console: Console | None = None
#     rich_error_console: Console | None = None

#     hidden: bool = False
#     help: str | None = None
#     help_epilog: str | None = None
#     help_section: str | None = None
#     deprecated: bool = False
#     add_help_option: bool = True

#     subcommands: dict[str, typing.Any] = dataclasses.field(default_factory=dict)

#     args: set[Arg] = dataclasses.field(default_factory=set) # TODO: make a dictionary of argument name/index to arg
#     var_args: VarArgs | None = dataclasses.field(default=None)
#     var_kwargs: VarKwargs | None = dataclasses.field(default=None)

#     pos_args: list[Arg] = dataclasses.field(init=False, default_factory=list)
#     kw_args: dict[str, Arg] = dataclasses.field(init=False, default_factory=dict)
#     env_args: dict[str, Arg] = dataclasses.field(init=False, default_factory=dict)
#     flag_args: dict[str, Arg] = dataclasses.field(init=False, default_factory=dict)

#     def __post_init__(self):

#         if len(self.args) > 0:
#             args = self.args
#             self.args = set()
#             for arg in args:
#                 self.add_arg(arg)

#     def define(self, func: _DECORATOR_INPUT) -> Spell:

#         assert self.func is None
#         assert not hasattr(func, SPELL_ATTR_NAME)

#         self.func = func
#         setattr(func, SPELL_ATTR_NAME, self)

#         for arg in getattr(func, ARG_ATTR_NAME, []):
#             self.add_arg(arg)

#         var_args = getattr(func, VAR_ARGS_ATTR_NAME, None)
#         if var_args is not None:
#             self.add_arg(var_args)

#         var_kwargs = getattr(func, VAR_KWARGS_ATTR_NAME, None)
#         if var_kwargs is not None:
#             self.add_arg(var_kwargs)

#         return self

#     def add_arg(self, arg: Arg | VarArgs | VarKwargs):

#         if isinstance(arg, VarArgs):
#             assert self.var_args is None
#             self.var_args = arg
#             return
        
#         if isinstance(arg, VarKwargs):
#             assert self.var_kwargs is None
#             self.var_kwargs = arg
#             return
        
#         assert arg not in self.args
#         self.args.add(arg)

#         if not arg.kwrd_only:
#             self.pos_args.append(arg)

#         if arg.name is not None:
#             assert arg.name not in self.kw_args
#             self.kw_args[arg.name] = arg
        
#         if arg.env_var is not None:
#             assert arg.env_var not in self.env_args
#             self.env_args[arg.env_var] = arg

#         if arg.flag_char is not None:
#             assert arg.flag_char not in self.flag_args
#             self.flag_args[arg.flag_char] = arg

#         for key in arg.aliases:
#             assert key not in self.kw_args
#             self.kw_args[key] = arg

#     def __call__(self, *args, **kwargs):
        
#         assert callable(self.func)

#         result = self.func(*args, **kwargs)

#         if self.print_result:
#             if self.rich_console is not None:
#                 self.rich_console.print(result)
#             else:
#                 print(result)

#         ## How does the error console fit in here? 

#         return result
    
#     def parse_args(self, *argv: str) -> tuple[tuple, dict[str, typing.Any], tuple[str, ...]]:

#         str_args = list[str]()
#         str_kwargs = dict[str, list[str]]()
#         flags = list[str]()
#         current_keyword: str | None = None

#         for i, arg in enumerate(argv):

#             if arg == SEPARATOR:
#                 break

#             if arg.startswith(KEYWORD_OPERATOR):

#                 kwarg = arg[len(KEYWORD_OPERATOR):]

#                 if KEYWORD_ASSIGNMENT_OPERATOR in kwarg:
#                     split = kwarg.split(KEYWORD_ASSIGNMENT_OPERATOR, 1)
#                     str_kwargs[split[0]] = [split[1]]
#                 else:
#                     current_keyword = kwarg
#                     str_kwargs[kwarg] = []

#                 continue

#             if arg.startswith(FLAG_OPERATOR):
#                 for flag in arg[len(FLAG_OPERATOR):]:
#                     flags.append(flag)
#                 continue

#             if current_keyword is not None:
#                 str_kwargs[current_keyword].append(arg)
#             else:
#                 str_args.append(arg)

#         remaining_args = argv[i:]

#         args = list()
#         kwargs = dict[str]()
#         used_args = set[Arg]()

#         if self.var_args is None:
#             assert len(self.pos_args) >= len(str_args)

#         for i, arg in str_args:

#             spell_arg = self.pos_args[i] if i <= len(self.pos_args) else self.var_args
#             try:
#                 parsed_arg = spell_arg.parser(arg)
#             except Exception as e:
#                 raise ParserError(e)

#             args.append(parsed_arg)

#             if not isinstance(spell_arg, VarKwargs):
#                 used_args.add(spell_arg)

#         for key, str_values in str_kwargs.items():

#             assert key in self.kw_args or self.var_kwargs is not None

#             spell_arg = self.kw_args.get(key, self.var_kwargs)

#             if not isinstance(spell_arg, VarKwargs):
#                 assert spell_arg not in used_args
#                 used_args.add(spell_arg)

#             assert isinstance(spell_arg.name, str)

#             if len(str_values) == 0:
#                 assert not isinstance(spell_arg, VarKwargs)
#                 if callable(spell_arg.flag_val):
#                     try:
#                         kwargs[spell_arg.name] = spell_arg.flag_val()
#                     except Exception as e:
#                         raise DefaultFactoryError(e)
#                 else:
#                     kwargs[spell_arg.name] = spell_arg.flag_val
#                 continue

#             try:
#                 kwargs[spell_arg.name] = spell_arg.parser(*str_values)
#             except Exception as e:
#                 raise ParserError(e)

#         for flag in flags:
            
#             assert flag in self.flag_args

#             spell_arg = self.flag_args[flag]

#             assert spell_arg not in used_args
#             used_args.add(spell_arg)

#             assert isinstance(spell_arg.name, str)

#             if callable(spell_arg.flag_val):
#                 try:
#                     kwargs[spell_arg.name] = spell_arg.flag_val()
#                 except Exception as e:
#                     raise DefaultFactoryError(e)
                
#             else:
#                 kwargs[spell_arg.name] = spell_arg.flag_val

#         if len(args) < len(self.pos_args):
#             for i in range(len(args), len(self.pos_args)):
#                 spell_arg = self.pos_args[i]
#                 assert spell_arg.default is not _NULL_VAL


#         for arg in self.args:
#             if arg in used_args:
#                 continue

#             assert arg.default is not _NULL_VAL

#             if callable(arg.default):
#                 try:
#                     default_val = arg.default()
#                 except Exception as e:
#                     raise DefaultFactoryError(e)
#             else:
#                 default_val = arg.default

#             if isinstance(arg.name, str):
#                 kwargs[arg.name] = default_val
#             else:
#                 assert arg in self.pos_args
#                 index = self.pos_args.index(arg)


#     def fire(
#         spell, 
#         *argv: str, 
#         serializer: typing.Callable[[typing.Any], str] | None = None,
#     ):
        
#         if not isinstance(spell, Spell):
#             spell = Spell().define(spell)

#         if len(argv) == 0:
#             argv = sys.argv[1:]

#         if len(argv) > 0:
#             subcommand = spell.subcommands.get(argv[0], _NULL_VAL)
#             if subcommand is not _NULL_VAL:
#                 return Spell.fire(subcommand)
            
        




#### v4 #######
# import os
# import sys
# import abc
# import typing
# import types
# import ast
# import inspect
# import pathlib
# import importlib
# import dataclasses

# if typing.TYPE_CHECKING:
#     from rich.console import Console

# SEPARATOR = '-'
# FLAG_OPERATOR = '-'
# KEYWORD_OPERATOR = '--'
# KEYWORD_ASSIGNMENT_OPERATOR = '='

# ARGS_ATTR_NAME = '__SPELL_ARGS__'
# VAR_ARGS_ATTR_NAME = '__SPELL_VAR_ARGS__'
# VAR_KWARGS_ATTR_NAME = '__SPELL_VAR_KWARGS__'
# SPELL_ATTR_NAME = '__SPELL__'

# _NULL_VAL = '__NULL__'
# _PARSER_TYPE = typing.TypeVar("_PARSER_TYPE")
# _DECORATOR_INPUT = typing.TypeVar("_DECORATOR_INPUT")

# __unused_sys_argv = sys.argv[1:]

# Ann = typing.Annotated

# class ParserError(Exception): ...
# class DefaultFactoryError(Exception): ...

# class Parser(abc.ABC, typing.Generic[_PARSER_TYPE]):
#     @abc.abstractmethod
#     def __call__(self, *argv: str) -> _PARSER_TYPE: ...

# class DefaultParser(Parser):
#     def __call__(self, *argv: str):
#         return ' '.join(argv) # TODO: Implement based on fire ast parser

# @dataclasses.dataclass(frozen=True, slots=True)
# class Arg:
#     name: str | None = None # If None, the arg is positional only
#     aliases: list[str] = dataclasses.field(default_factory=list)
#     env_var: str | None = None
#     flag_char: str | None = None
    
#     parser: Parser = dataclasses.field(default_factory=DefaultParser)
#     default: typing.Any | typing.Callable[[], typing.Any] = _NULL_VAL
#     flag_val: typing.Any | typing.Callable[[], typing.Any] = True
    
#     hidden: bool = False
#     help: str | None = None
#     help_section: str | None = None

#     kwrd_only: bool = False
    
#     def __post_init__(self):

#         if self.name is None:
#             assert not self.kwrd_only
#             assert len(self.aliases) == 0
#             assert self.flag_char is None

#         elif self.flag_char is not None:
#             assert len(self.flag_char) == 1

#     def __call__(self, func: _DECORATOR_INPUT, index=0) -> _DECORATOR_INPUT:
#         args = getattr(func, ARGS_ATTR_NAME, [])
#         args.insert(self, index)
#         setattr(func, ARGS_ATTR_NAME, args)

#     def get_default_val(self):
#         if callable(self.default):
#             return self.default()
#         else:
#             return self.default

#     def get_flag_val(self):
#         if callable(self.flag_val):
#             return self.flag_val()
#         else:
#             return self.flag_val

#     def var_args(self, func: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         assert not hasattr(func, VAR_ARGS_ATTR_NAME)
#         setattr(func, VAR_ARGS_ATTR_NAME, self)
#         return func

#     def var_kwargs(self, func: _DECORATOR_INPUT) -> _DECORATOR_INPUT:
#         assert not hasattr(func, VAR_KWARGS_ATTR_NAME)
#         setattr(func, VAR_KWARGS_ATTR_NAME, self)
#         return func

# def VarArgs(
#     parser: Parser | None = None,
#     hidden: bool = False,
#     help: str | None = None,
#     help_section: str | None = None,
# ) -> typing.Callable[[_DECORATOR_INPUT], _DECORATOR_INPUT]:
    
#     if parser is None:
#         parser = DefaultParser()
    
#     arg = Arg(
#         parser=parser,
#         hidden=hidden,
#         help=help,
#         help_section=help_section,
#     )

#     return arg.var_args

# def VarKwargs(
#     parser: Parser | None = None,
#     flag_val: typing.Any | typing.Callable[[], typing.Any] = True,
#     hidden: bool = False,
#     help: str | None = None,
#     help_section: str | None = None,
# ):
#     if parser is None:
#         parser = DefaultParser()
    
#     arg = Arg(
#         parser=parser,
#         flag_val=flag_val,
#         hidden=hidden,
#         help=help,
#         help_section=help_section,
#     )

#     return arg.var_kwargs

# class ResultHandler(abc.ABC):
#     @abc.abstractmethod
#     def __call__(self, result, *argv: str) -> typing.Any: ...

# @dataclasses.dataclass()
# class Spell:
#     name: str | None = None

#     source: typing.Any = _NULL_VAL
#     result_handler: ResultHandler | None = None

#     hidden: bool = False
#     help: str | None = None
#     help_epilog: str | None = None
#     help_section: str | None = None
#     deprecated: bool = False
#     add_help_option: bool = True

#     subcommands: dict[str, typing.Any] = dataclasses.field(default_factory=dict)

#     # Arg attributes should be read only after initialization
#     # Therefore all Args should be set before creating the spell
#     args: set[Arg] = dataclasses.field(default_factory=set)
#     var_args: Arg | None = dataclasses.field(default=None)
#     var_kwargs: Arg | None = dataclasses.field(default=None)

#     pos_args: list[Arg] = dataclasses.field(init=False, default_factory=list)
#     kw_args: dict[str, Arg] = dataclasses.field(init=False, default_factory=dict)
#     env_args: dict[str, Arg] = dataclasses.field(init=False, default_factory=dict)
#     flag_args: dict[str, Arg] = dataclasses.field(init=False, default_factory=dict)

#     DEFAULT_HALT_TYPES = typing.ClassVar[set[type]] = set([
#         bool,
#         int,
#         float,
#         complex,
#         str,
#         bytes,
#         bytearray,
#         pathlib.Path,
#     ])

#     def define(self, source) -> Spell:
#         assert self.source is _NULL_VAL
#         self.source = source

#         for arg in reversed(getattr(source, ARGS_ATTR_NAME, [])):

#             assert isinstance(arg, Arg)

#             self.args.add(arg)

#             if not arg.kwrd_only:
#                 self.pos_args.append(arg)

#             if arg.name is not None:
#                 for key in [arg.name] + arg.aliases:
#                     assert key not in self.kw_args
#                     self.kw_args[key] = arg

#                 if arg.flag_char is not None:
#                     assert arg.flag_char not in self.flag_args
#                     self.flag_args[arg.flag_char] = arg

#             if arg.env_var is not None:
#                 assert arg.env_var not in self.env_args
#                 self.env_args[arg.env_var] = arg

#         return self

#     def parse_argv(self, *argv: str) -> tuple[list, dict[str], list[str]]:
#         parsed_args = list()
#         parsed_kwargs = dict[str]()

#         remaining_args = self.args.copy()
#         current_arg: Arg | None = None
#         current_kwargv = list[str]()
#         pos_arg_index = 0

#         def flush_kwargv():
#             nonlocal parsed_kwargs
#             nonlocal remaining_args
#             nonlocal current_arg
#             nonlocal current_kwargv

#             if current_arg is None:
#                 return 

#             key = current_arg.name
            
#             if len(current_kwargv) > 0:
#                 parsed_kwargs[key] = current_arg.parser(*current_kwargv)
#             else:
#                 parsed_kwargs[key] = current_arg.get_flag_val()

#             remaining_args.discard(current_arg)
#             current_arg = None
#             current_kwargv = []

#         for i, arg in enumerate(argv):

#             if arg == SEPARATOR:
#                 break

#             if arg.startswith(KEYWORD_OPERATOR):
#                 flush_kwargv()

#                 key = arg[len(KEYWORD_OPERATOR):]

#                 if key in self.kw_args:
#                     current_arg = self.kw_args[key]
#                     assert current_arg in remaining_args
#                 else:
#                     assert self.var_kwargs is not None
#                     current_arg = self.var_kwargs

#                 continue

#             if arg.startswith(FLAG_OPERATOR) and current_arg is None:
#                 # assert current_arg is None, "Flags must be invoked outside keyword arguments"
#                 for char in arg[len(FLAG_OPERATOR):]:
#                     assert char in self.flag_args
#                     flag_arg = self.flag_args[char]
#                     assert flag_arg in remaining_args
#                     parsed_kwargs[flag_arg.name] = flag_arg.get_flag_val()
#                     remaining_args.remove(flag_arg)
#                 continue

#             if current_arg is not None:
#                 current_kwargv.append(arg)
#                 continue

#             # Positional
#             if pos_arg_index < len(self.pos_args):
#                 pos_arg = self.pos_args[pos_arg_index]
#                 assert pos_arg in remaining_args
#             else:
#                 assert self.var_args is not None
#                 pos_arg = self.var_args

#             parsed_args.append(pos_arg.parser(arg))
#             remaining_args.discard(pos_arg)
#             pos_arg_index += 1

#         flush_kwargv()
#         remaining_argv = list(argv[i:])

#         for arg in remaining_args:

#             if arg.env_var is not None and arg.env_var in os.environ:
#                 val = arg.parser(os.environ[arg.env_var])
#             else:
#                 assert arg.default is not _NULL_VAL
#                 val = arg.get_default_val()

#             if arg.name is None:
#                 parsed_args.append(val)
#             else:
#                 parsed_kwargs[arg.name] = val

#         return parsed_args, parsed_kwargs, remaining_argv

#     def __call__(self, *args, **kwargs):
#         assert callable(self.source)
#         return self.source(*args, **kwargs)

#     def Fire(source, *argv: str):

#         global __unused_sys_argv

#         if len(argv) == 0 and len(__unused_sys_argv) > 0:
#             argv = __unused_sys_argv
#             __unused_sys_argv = []

#         if not isinstance(source, Spell):
#             source = Spell().define(source)

#         if len(argv) > 0 and argv[0] in source.subcommands:
#             result = source.subcommands[argv[0]]
#             rem_argv = argv[1:]
#         else:
#             args, kwargs, rem_argv = source.parse_argv(*argv)
#             result = source.__call__(*args, **kwargs)

#         if source.result_handler is not None:
#             return source.result_handler(result, *rem_argv)
#         else:
#             return Spell.Fire(result, *rem_argv)
