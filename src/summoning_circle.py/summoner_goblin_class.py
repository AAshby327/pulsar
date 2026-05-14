import typing
import logging
import threading

import rich.progress

from spell_book_class import SpellBook, BrokenSpellBook

class SummonerGoblin:

    task_id: rich.progress.TaskID
    spell_book: SpellBook

    status: float | None
    bar_style: str
    logger: logging.Logger

    completion_horn: threading.Event

    _claimed: bool
    _waiting_for: list[SpellBook]

    def __init__(
            self,
            task_id: rich.progress.TaskID,
            spell_book: SpellBook,
    ):
        
        self.task_id = task_id
        self.spell_book = spell_book
        assert not isinstance(self.spell_book, BrokenSpellBook)

        self.status = None
        self.bar_style = 'bar.complete'
        
        if spell_book.logger:
            self.logger = spell_book.logger
        else: 
            self.logger = logging.getLogger(f'library.{spell_book.name}')

        self.completion_horn = threading.Event()
        self._claimed = False
        self._waiting_for = []