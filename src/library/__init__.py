import sys
import importlib

import rich.traceback

import pulsar_env
from spell_book_class import SpellBook, BrokenSpellBook

catalog: dict[str, SpellBook] = dict()

def import_all():
    library_path = pulsar_env.PULSAR_SRC_DIR / 'library'
    
    for module in library_path.iterdir():

        if module.name == '__init__.py' \
        or module.is_file() and module.suffix != '.py' \
        or module.is_dir() and not (module / '__init__.py').exists() \
        or module.name in sys.modules:
            continue

        try:
            importlib.import_module(f'library.{module.stem}')
        except Exception as e:
            catalog.pop(module.stem, None)
            BrokenSpellBook(module.stem, e, rich.traceback.Traceback())