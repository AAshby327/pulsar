import time
import threading
from concurrent import futures

import rich.progress

import pulsar_console
import library
from spell_book_class import SpellBook, BrokenSpellBook
from summoning_circle.summoner_goblin_class import SummonerGoblin
from summoning_circle.progress_columns import ProgressBarColumn, PercentColumn, LogColumn


queued_spell_books: list[SpellBook] = []

def __futures_handler(
    future_to_goblin: dict[futures.Future, SummonerGoblin],
    progress: rich.progress.Progress,
    stop_event: threading.Event,
):
    for future in futures.as_completed(future_to_goblin):
        goblin = future_to_goblin[future]

        try:
            result = future.result()
            if not goblin._completion_horn.is_set():
                goblin.complete()
        except Exception as e: 
            goblin.fail(e)
        finally:
            task = progress._tasks[goblin.task_id]
            task.finished_time = task.elapsed # Mark task as complete

    stop_event.set()

def install_spell_books(
    spell_books: list[SpellBook],
    reinstall: bool,
    no_cache: bool,
    max_workers: int,
):
    global queued_spell_books

    library.import_all()

    # Include dependencies
    for sb in spell_books:
        for dep in sb.dependencies:

            if isinstance(dep, str):
                dep = library.catalog[dep]

            if dep not in spell_books:
                spell_books.append(dep)

    assert all(not isinstance(sb, BrokenSpellBook) for sb in spell_books)

    # Topological sort: dependencies before dependents
    sorted_books = []
    visited = set()

    def visit(sb: SpellBook):
        if sb in visited:
            return
        visited.add(sb)

        for dep in sb.dependencies:
            if isinstance(dep, str):
                dep = library.catalog[dep]
            visit(dep)

        sorted_books.append(sb)

    for sb in spell_books:
        visit(sb)

    spell_books = queued_spell_books = sorted_books

    progress = rich.progress.Progress(
        rich.progress.SpinnerColumn(),
        rich.progress.TextColumn('{task.description}'),
        ProgressBarColumn(bar_width=30),
        PercentColumn(),
        rich.progress.TimeElapsedColumn(),
        LogColumn(),
        console=pulsar_console.console,
        transient=False,
    )
        
    with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

        progress.start()

        goblin_team = [
            SummonerGoblin(
                progress.add_task(sb.name, total=None),
                sb, reinstall, no_cache,
            ) 
            for sb in spell_books 
            if sb._installer_spell is not None
        ]

        future_to_goblin = {
            executor.submit(goblin.spell_book._installer_spell) : goblin
            for goblin in goblin_team
        }
        
        stop_event = threading.Event()
        future_thread = threading.Thread(
            target=__futures_handler,
            args=(future_to_goblin, progress, stop_event),
            daemon=True,
        )

        future_thread.start()

        while not stop_event.is_set():
            for goblin in goblin_team:
                progress.update(goblin.task_id, goblin=goblin)
            time.sleep(0.1)

        future_thread.join()
        progress.stop()

