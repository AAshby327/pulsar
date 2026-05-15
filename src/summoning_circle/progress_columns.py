import typing 
import logging

import rich.text
import rich.table
import rich.progress
from rich.progress_bar import ProgressBar

from summoning_circle.summoner_goblin_class import SummonerGoblin

def get_worker_goblin(task: rich.progress.Task) -> SummonerGoblin | None:
    return task.fields.get('goblin', None)


class ProgressBarColumn(rich.progress.ProgressColumn):

    def __init__(
        self, 
        bar_width = 40,
        table_column: typing.Optional[rich.table.Column] = None,
    ):

        super().__init__(table_column)

        self.bar_width = bar_width

        self.bars: dict[rich.progress.TaskID, ProgressBar] = dict()

    def render(self, task):

        if task.id not in self.bars:
            self.bars[task.id] = ProgressBar(
                total=1.0,
                completed=0.0,
                width=self.bar_width,
            )

        bar = self.bars[task.id]
        goblin = get_worker_goblin(task)

        if goblin is None:
            bar.pulse = True
            return bar
        
        if goblin._completion_horn.is_set():
            bar.pulse = False
            if goblin.error is None:
                bar.completed = 1.0
                bar.finished_style = 'bar.finished'
            else: 
                bar.finished_style = 'red'
                bar.style = 'dim red'
            return bar
        
        if len(goblin._waiting_for) > 0:
            names = ", ".join(sb.name for sb in goblin._waiting_for)
            text = f"[waiting: {names}]"

            if len(text) > bar.width:
                text = text[:self.bar_width-4] + '...]'

            return rich.text.Text(text, style='dim blue')
        
        if goblin.status is None:
            bar.pulse = True
        else: 
            bar.pulse = False
            bar.completed = goblin.status
        
        bar.complete_style = goblin.bar_style
        bar.pulse_style = goblin.bar_style

        return bar
    
    
class PercentColumn(rich.progress.ProgressColumn):

    def __init__(
        self, 
        table_column: typing.Optional[rich.table.Column] = None,
    ):
        super().__init__(table_column)

    def render(self, task):
        goblin = get_worker_goblin(task)

        if goblin is None or goblin.status is None:
            return rich.text.Text(" ---")
        
        return rich.text.Text(f"{goblin.status*100:>3.0f}%", style='progress.percentage')
    
class LogColumn(rich.progress.ProgressColumn):

    class _LastLogHandler(logging.Handler):
        def __init__(self, logger: logging.Logger):
            super().__init__(level=logging.INFO)
            self.last_log = ''
            self.logger = logger

        def emit(self, record):
            try:
                self.last_log = self.format(record)
            except Exception:
                self.handleError(record)

        def update_logger(self, new_logger: logging.Logger):
            self.logger.removeHandler(self)
            self.logger = new_logger
            self.logger.addHandler(self)


    def __init__(
        self, 
        table_column: typing.Optional[rich.table.Column] = None,
    ):
        super().__init__(table_column)
        self.handlers: dict[SummonerGoblin, LogColumn._LastLogHandler] = dict()

    def render(self, task):
        goblin = get_worker_goblin(task)

        if goblin is None: 
            return ''
        
        if goblin in self.handlers:
            if self.handlers[goblin].logger is not goblin.logger:
                self.handlers[goblin].update_logger(goblin.logger)
        else:
            self.handlers[goblin] = LogColumn._LastLogHandler(goblin.logger)

        lines = self.handlers[goblin].last_log.splitlines()

        if len(lines) == 0:
            return ''

        return rich.text.Text(
            lines[-1],
            style='dim',
        )

