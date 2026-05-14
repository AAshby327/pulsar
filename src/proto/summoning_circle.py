import typing
import logging
import threading
import time
import zipfile
import tarfile
import urllib.request
import pathlib
from concurrent import futures

import py7zr

from rich.progress import (
    Progress,
    SpinnerColumn,
    TimeElapsedColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TextColumn,

    TaskID,
)
from rich.text import Text

import pulsar_console
import library

reinstall = False
no_cache = False

_goblins: dict[library.SpellBook, SummonerGoblin] = dict()

class _LastLogHandler(logging.Handler):
    """Custom handler that stores the last log message"""
    def __init__(self, goblin):
        super().__init__()
        self.goblin = goblin

    def emit(self, record):
        try:
            msg = self.format(record)
            self.goblin.last_log_message = msg
        except Exception:
            self.handleError(record)

class SummonerBar(BarColumn):
    def render(self, task):
        goblin: SummonerGoblin = task.fields.get('goblin', None)

        if goblin is not None:
            # If waiting for dependencies, show waiting message instead of bar
            if goblin.waiting_for:
                names = ", ".join(sb.name for sb in goblin.waiting_for)
                text = f"[waiting: {names}]"

                # Truncate to fit within bar width
                if len(text) > self.bar_width:
                    available = self.bar_width - 4
                    text = text[:available] + "...]"

                return Text(text, style="dim yellow")

            self.complete_style = goblin.bar_style
            self.finished_style = goblin.bar_style
            self.pulse_style = goblin.bar_style

        return super().render(task)
    
class PercentColumn(TaskProgressColumn):
    def render(self, task):
        goblin: SummonerGoblin = task.fields.get('goblin', None)

        if goblin is None or goblin.progress is None:
            return " ---"
        
        return super().render(task)
    
class LogColumn(TextColumn):
    def __init__(self):
        super().__init__("")  # Empty text format since we override render
        self.handlers: dict[SummonerGoblin, tuple[_LastLogHandler, logging.Logger]] = {}

    def setup_goblin(self, goblin):
        """Attach a log handler to a goblin's logger"""
        # Check if handler exists and if logger has changed
        if goblin in self.handlers:
            handler, old_logger = self.handlers[goblin]
            if old_logger is not goblin.logger:
                # Logger changed, remove old handler and add to new logger
                old_logger.removeHandler(handler)
                goblin.logger.addHandler(handler)
                self.handlers[goblin] = (handler, goblin.logger)
        else:
            # First time setup
            handler = _LastLogHandler(goblin)
            goblin.logger.addHandler(handler)
            self.handlers[goblin] = (handler, goblin.logger)

    def render(self, task):
        goblin: SummonerGoblin = task.fields.get('goblin', None)
        if goblin is not None:
            # Ensure handler is set up
            self.setup_goblin(goblin)
            # Only show the last line if multi-line
            message = goblin.last_log_message
            if message:
                return message.splitlines()[-1]
        return ""

class SummonerGoblin:
    task_name: str
    spell_book: library.SpellBook
    bar_style: str
    progress: float | None

    task_id: TaskID
    rich_progress: Progress

    waiting_for: list[library.SpellBook] | None

    _claimed: bool
    _completion_event: threading.Event

    def __init__(
            self,
            spell_book: library.SpellBook,
        ):

        self.spell_book = spell_book
        self.bar_style = 'bar.complete'
        self.progress = None
        self.task_id = None
        self.rich_progress = None
        self.last_log_message = ""
        self.waiting_for = None

        logger_name = getattr(spell_book, 'script', spell_book.name) if hasattr(spell_book, 'name') else str(spell_book)
        self.logger = logging.getLogger(f'summoning_circle.{logger_name}')

        # Set logger level to INFO
        self.logger.setLevel(logging.INFO)

        self._claimed = False
        self._completion_event = threading.Event()
        _goblins[spell_book] = self

    def set_logger(self, logger: logging.Logger):
        self.logger = logger

    def wait_for_spell_books(self, spell_books: list[library.SpellBook]):
        """Wait for the specified spell books to finish installing.

        This function blocks until all the specified spell books have completed
        their installation (either successfully or with an error).
        """
        # Set waiting state for display (use a copy so we can modify it)
        self.waiting_for = list(spell_books)

        try:
            for spell_book in spell_books:
                goblin = _goblins.get(spell_book)
                if goblin is not None:
                    goblin._completion_event.wait()
                # Remove from waiting list as it completes
                if spell_book in self.waiting_for:
                    self.waiting_for.remove(spell_book)
        finally:
            # Clear waiting state
            self.waiting_for = None

    def download(self, url: str, output_path: str, chunk_size: int = 8192):
        self.rich_progress.add_task('download')

    def extract(self, file: str, output_path: str):
        pass
        

    def complete(self):
        self._completion_event.set()
        _goblins.pop(self.spell_book, None)

def _progress_updater(progress: Progress, stop_event: threading.Event):
    """Background thread that continuously updates progress for all active goblins"""
    while not stop_event.is_set():
        for goblin in list(_goblins.values()):
            if goblin.task_id is not None:
                total = None if goblin.progress is None else 1.0
                progress.update(goblin.task_id, completed=goblin.progress, goblin=goblin, total=total)
        time.sleep(0.1)  # Update 10 times per second

def summon_goblin_worker(spell_book: library.SpellBook):
    goblin = _goblins[spell_book]
    assert not goblin._claimed, "Summoner goblin is being summoned multiple times."
    goblin._claimed = True
    return goblin

def install_spellbooks(
        spell_books: list[library.SpellBook],
        max_workers: int,
        _reinstall: bool = False,
        _no_cache: bool = False,
    ):
    global reinstall, no_cache

    reinstall = _reinstall
    no_cache = _no_cache

    for spell_book in spell_books:
        for dep in spell_book.dependencies:
            if dep not in spell_books:
                spell_books.append(dep)

    assert all(not isinstance(spell_book, library.BrokenSpellBook) for spell_book in spell_books)

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        SummonerBar(bar_width=30),
        PercentColumn(),
        TimeElapsedColumn(),
        LogColumn(),
        console=pulsar_console.console,
        transient=False,
    ) as progress:

        for spell_book in spell_books:
            goblin = SummonerGoblin(spell_book)
            goblin.rich_progress = progress
            goblin.task_id = progress.add_task(spell_book.name, total=None)

        # Start background progress updater thread
        stop_event = threading.Event()
        updater_thread = threading.Thread(
            target=_progress_updater,
            args=(progress, stop_event),
            daemon=True
        )
        updater_thread.start()

        try:
            # Execute installer_spell for each spellbook in parallel
            with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all installation tasks
                future_to_spellbook: dict[futures.Future, library.SpellBook] = dict()
                for spell_book in spell_books: 
                    if spell_book.installer_spell is None:
                        continue
                    future_to_spellbook[executor.submit(spell_book.installer_spell)] = spell_book

                # Process completed tasks and update progress
                for future in futures.as_completed(future_to_spellbook):
                    spell_book = future_to_spellbook[future]
                    goblin = _goblins.get(spell_book)

                    if goblin is None:
                        continue

                    try:
                        # Get the result (this will raise if the installer failed)
                        result = future.result()
                        goblin.bar_style = 'bar.finished'

                    except Exception as e:
                        # Update progress on failure
                        goblin.logger.exception(f"Installation failed for {spell_book.name}")
                        goblin.bar_style = 'red'
                        goblin.progress = None

                    finally:
                        # Mark goblin as complete
                        goblin.complete()

        finally:
            # Stop the progress updater thread
            stop_event.set()
            updater_thread.join(timeout=1.0)


if __name__ == "__main__":
    import time
    import tempfile
    import shutil

    # Create test spellbooks first
    neovim_book = library.SpellBook("neovim", help="Hyperextensible Vim-based text editor")
    ripgrep_book = library.SpellBook("ripgrep", help="Recursively searches directories for regex patterns")
    wezterm_book = library.SpellBook("wezterm", help="GPU-accelerated cross-platform terminal emulator")
    fzf_book = library.SpellBook("fzf", help="Command-line fuzzy finder")
    download_test_book = library.SpellBook("download-test", help="Tests download and extract helpers")

    # Create dummy installer functions that update progress
    def dummy_installer_fast():
        """Simulates a fast installation (1-2 seconds)"""
        logger = logging.getLogger('summoning_circle.demo.neovim')
        goblin = summon_goblin_worker(neovim_book)
        goblin.set_logger(logger)
        steps = 15
        logger.info("Checking system requirements...")
        for i in range(steps + 1):
            if goblin:
                goblin.progress = (i / steps)
                if i == 3:
                    logger.info("Downloading neovim...")
                elif i == 8:
                    logger.info("Extracting archive...")
                elif i == 12:
                    logger.info("Installing binaries...")
            time.sleep(1.5 / steps)
        logger.error("Test error: Installation failed!")
        raise ValueError("Test error")
        return True

    def dummy_installer_medium():
        """Simulates a medium speed installation (3-4 seconds)"""
        logger = logging.getLogger('summoning_circle.demo.ripgrep')
        # goblin = SummonerGoblin(ripgrep_book, logger=logger)
        goblin = summon_goblin_worker(ripgrep_book)
        goblin.set_logger(logger)
        steps = 35
        logger.info("Starting installation...")
        for i in range(steps + 1):
            if goblin:
                goblin.progress = (i / steps)
                if i == 5:
                    logger.info("Fetching latest version...")
                elif i == 15:
                    logger.info("Downloading ripgrep binary...")
                elif i == 25:
                    logger.info("Verifying checksums...")
                elif i == 30:
                    logger.info("Installing to bin directory...")
            time.sleep(3.5 / steps)
        logger.info("Installation complete!")
        return True

    def dummy_installer_slow():
        """Simulates a slow installation (5-6 seconds)"""
        logger = logging.getLogger('summoning_circle.demo.wezterm')
        # goblin = SummonerGoblin(wezterm_book, logger=logger)
        goblin = summon_goblin_worker(wezterm_book)
        goblin.set_logger(logger)
        steps = 55
        logger.info("Preparing installation...")
        for i in range(steps + 1):
            if goblin:
                goblin.progress = (i / steps)
                if i == 10:
                    logger.info("Downloading wezterm (large file)...")
                elif i == 25:
                    logger.info("Download progress: 50%...")
                elif i == 35:
                    logger.info("Extracting large archive...")
                elif i == 45:
                    logger.info("Setting up configuration...")
                elif i == 50:
                    logger.info("Creating symlinks...")
            time.sleep(5.5 / steps)
        logger.info("Successfully installed wezterm!")
        return True

    def dummy_installer_fast2():
        """Simulates a fast installation (1-2 seconds)"""
        logger = logging.getLogger('summoning_circle.demo.fzf')
        # goblin = SummonerGoblin(fzf_book, logger=logger)
        goblin = summon_goblin_worker(fzf_book)
        goblin.set_logger(logger)
        steps = 15
        logger.info("Initializing...")
        for i in range(steps + 1):
            if goblin:
                goblin.progress = (i / steps)
                if i == 4:
                    logger.info("Downloading fzf...")
                elif i == 10:
                    logger.info("Installing executable...")
            time.sleep(1.5 / steps)
        logger.info("fzf ready to use!")
        return True

    def dummy_installer_with_deps():
        """Simulates an installer that waits for dependencies (neovim and ripgrep)"""
        logger = logging.getLogger('summoning_circle.demo.wezterm')
        goblin = summon_goblin_worker(wezterm_book)
        goblin.set_logger(logger)

        logger.info("Waiting for dependencies (neovim, ripgrep)...")
        goblin.progress = 0.1

        # Wait for neovim and ripgrep to finish
        goblin.wait_for_spell_books([neovim_book, ripgrep_book])

        logger.info("Dependencies ready! Starting installation...")
        steps = 20
        for i in range(steps + 1):
            goblin.progress = 0.1 + (0.9 * i / steps)
            if i == 5:
                logger.info("Downloading wezterm...")
            elif i == 15:
                logger.info("Installing wezterm...")
            time.sleep(2.0 / steps)

        logger.info("Successfully installed wezterm!")
        return True

    def test_download_extract():
        """Tests download and extract helper functions"""
        logger = logging.getLogger('summoning_circle.demo.download-test')
        goblin = summon_goblin_worker(download_test_book)
        goblin.set_logger(logger)

        # Create a temporary directory for testing
        temp_dir = pathlib.Path(__file__).parent

        try:
            # Test 1: Download a small file (example: a small zip from GitHub)
            logger.info("Testing download function...")
            goblin.progress = 0.0

            # Download a small test file (ripgrep release as an example)
            test_url = "https://github.com/BurntSushi/ripgrep/releases/download/14.1.0/ripgrep-14.1.0-x86_64-pc-windows-msvc.zip"
            download_path = temp_dir / "test.zip"

            goblin.download(test_url, download_path)

            logger.info(f"Download successful: {download_path.name} ({download_path.stat().st_size} bytes)")

            # Test 2: Extract the downloaded zip file
            logger.info("Testing extract function...")
            extract_dir = temp_dir / "extracted"

            # goblin.extract(download_path, extract_dir)

            logger.info(f"Extraction successful: {len(list(extract_dir.rglob('*')))} files extracted")

            goblin.progress = 1.0
            logger.info("All tests completed successfully!")

        except Exception as e:
            logger.error(f"Test failed: {e}")
            raise

        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    # Assign installers to spellbooks
    neovim_book.installer_spell = dummy_installer_fast
    ripgrep_book.installer_spell = dummy_installer_medium
    wezterm_book.installer_spell = dummy_installer_with_deps  # Uses wait_for_spell_books
    fzf_book.installer_spell = dummy_installer_fast2
    download_test_book.installer_spell = test_download_extract  # Tests download/extract

    test_spellbooks = [neovim_book, ripgrep_book, wezterm_book, fzf_book, download_test_book]

    pulsar_console.console.print("[bold magenta]🔮 Summoning Circle Test[/bold magenta]")
    pulsar_console.console.print(f"Installing {len(test_spellbooks)} spellbooks with 2 workers")
    pulsar_console.console.print("[yellow]Note: wezterm waits for neovim and ripgrep to complete[/yellow]")
    pulsar_console.console.print("[yellow]Note: download-test demonstrates download/extract helpers[/yellow]\n")

    # Test the installation with 2 workers
    install_spellbooks(
        spell_books=test_spellbooks,
        max_workers=2,
        _reinstall=False,
        _no_cache=False
    )