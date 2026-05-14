import logging
import threading

import rich.progress

from spell_book_class import SpellBook, BrokenSpellBook

_hoard: dict[SpellBook, SummonerGoblin] = dict()

def summon_goblin_worker(spell_book: SpellBook) -> SummonerGoblin | None:
    goblin = _hoard.get(spell_book)
    if goblin is None:
        return None
    
    assert not goblin._claimed
    goblin._claimed = True
    return goblin

class DependencyError(Exception): pass

class SummonerGoblin:

    task_id: rich.progress.TaskID
    spell_book: SpellBook

    status: float | None
    bar_style: str
    error: Exception | str | None
    logger: logging.Logger

    reinstall_command: bool
    no_cache_command: bool

    _completion_horn: threading.Event
    _claimed: bool
    _waiting_for: list[SpellBook]

    def __init__(
        self,
        task_id: rich.progress.TaskID,
        spell_book: SpellBook,
        reinstall: bool = False,
        no_cache: bool = False,
    ):
        
        self.task_id = task_id
        self.spell_book = spell_book
        assert not isinstance(self.spell_book, BrokenSpellBook)
        assert self.spell_book not in _hoard

        _hoard[self.spell_book] = self

        self.status = None
        self.bar_style = 'bar.complete'
        self.error = None
        
        if spell_book.logger:
            self.logger = spell_book.logger
        else: 
            self.logger = logging.getLogger(f'library.{spell_book.name}')

        self.reinstall_command = reinstall
        self.no_cache_command = no_cache

        self._completion_horn = threading.Event()
        self._claimed = False
        self._waiting_for = list()

    def wait_for_spell_books(self, spell_books: list[SpellBook]):

        from summoning_circle.install_process import queued_spell_books

        assert all(sb in queued_spell_books for sb in spell_books)
        assert not any(sb is self.spell_book for sb in spell_books)

        self._waiting_for = sorted(spell_books, key=
            lambda sb: queued_spell_books.index(sb))
        
        dep_finished = threading.Event()

        def set_thread(e: threading.Event):
            e.wait()
            dep_finished.set()

        for sb in self._waiting_for:
            threading.Thread(
                target=set_thread,
                args=(_hoard[sb]._completion_horn,),
                daemon=True,
            ).start()

        while len(self._waiting_for) > 0:

            dep_finished.wait(1.0)

            for sb in self._waiting_for.copy():
                if _hoard[sb]._completion_horn.is_set():
                    self._waiting_for.remove(sb)

            dep_finished.clear()
    
    def complete(self):
        self._completion_horn.set()
        self.bar_style = 'bar.finished'

    def fail(self, error: Exception | str):
        self._completion_horn.set()
        self.bar_style = 'red'
        self.error = error
        msg = f"Install failed for {self.spell_book.name}"
        if isinstance(error, Exception):
            self.logger.exception(msg)
        else:
            self.logger.error(msg)
