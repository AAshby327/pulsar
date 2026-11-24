import typing
import enum
import signal
import time
import traceback
import dataclasses
import multiprocessing

if typing.TYPE_CHECKING:
    from multiprocessing.context import SpawnProcess, SpawnContext
    from multiprocessing.connection import PipeConnection

    from rich.text import Text
    from rich.progress_bar import ProgressBar

    DECORATOR_INPUT = typing.TypeVar('DECORATOR_INPUT', bound=typing.Callable)


__all__ = [
    'Ritual',
    'Installer',
    'SummonerGoblin',
    'SummoningCircle',
]


class _RITUAL_STATE(enum.Enum):
    PENDING = enum.auto()
    RUNNING = enum.auto()
    COMPLETED = enum.auto()
    FAILED = enum.auto()


@dataclasses.dataclass
class Ritual[**P]:
    callback: typing.Callable[P, None] | None = None

    progress: float | None = None
    status: str = ''
    error: str | None = None
    traceback: str | None = None

    _state: _RITUAL_STATE = _RITUAL_STATE.PENDING

    def __hash__(self):
        return id(self)

    def bind(self, callback: DECORATOR_INPUT) -> DECORATOR_INPUT:
        self.callback = callback
        return callback


class Installer:
    name: str
    build_dependencies: set[Installer]

    summon_ritual: Ritual[[SummonerGoblin]]
    install_ritual: Ritual[[SummonerGoblin]]
    abort_ritual: Ritual[[]]

    def __init__(
        self,
        name: str,
        build_dependencies: set[Installer] = None,
    ):
        self.name = name
        self.build_dependencies = build_dependencies \
            if build_dependencies is not None else set()

        self.summon_ritual = Ritual()
        self.install_ritual = Ritual()
        self.abort_ritual = Ritual()


@dataclasses.dataclass
class SummonerGoblin:
    _callback: typing.Callable[[SummonerGoblin], None] | None = None
    _main_thread_connection: PipeConnection | None = None

    def report_progress(self, progress: float | None):
            self._main_thread_connection.send({'progress': progress})

    # TODO: Add to a logger
    def report_status(self, status: str):
        self._main_thread_connection.send({'status': status})


@dataclasses.dataclass
class _GoblinConnection:
    ritual: Ritual | None = None
    process: SpawnProcess | None = None
    connection: PipeConnection | None = None

    goblin: SummonerGoblin = dataclasses.field(
        default_factory=lambda: SummonerGoblin()
    )

    def release_ritual(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except OSError:
                pass

            self.connection = None

        if self.process is not None:
            if self.process.is_alive():
                self.process.join(1.0)

            if not self.process.is_alive():
                self.process.join()

                try:
                    self.process.close()
                except (ValueError, OSError):
                    pass

            self.process = None

        self.ritual = None
        self.goblin._callback = None
        self.goblin._main_thread_connection = None


def _execute_ritual(goblin: SummonerGoblin):
    # Prevent Ctrl+C from generating worker tracebacks.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        goblin._callback(goblin)
        goblin._main_thread_connection.send({'_state': _RITUAL_STATE.COMPLETED})

    except BaseException as e:
        try:
            goblin._main_thread_connection.send({
                '_state': _RITUAL_STATE.FAILED,
                'error': f'{type(e).__name__}: {e}',
                'traceback': traceback.format_exc(),
            })

        except (BrokenPipeError, EOFError, OSError):
            pass

    finally:
        goblin._main_thread_connection.close()


class SummoningCircle:

    _ctx: SpawnContext
    _worker_goblins: list[_GoblinConnection]

    _installers: set[Installer]
    _rituals: dict[Ritual[SummonerGoblin], set[Ritual[SummonerGoblin]]] # Ritual -> Prerequisites

    _aborted: bool

    _progress_bars: dict[Installer, ProgressBar] | None
    _status_messages: dict[Installer, Text] | None

    def __init__(self, max_workers=multiprocessing.cpu_count()):

        assert max_workers >= 1

        self._ctx = multiprocessing.get_context('spawn')
        self._worker_goblins = [
            _GoblinConnection()
            for _ in range(max_workers)
        ]

        self._installers = set()
        self._rituals = dict()

        self._aborted = False

        self._progress_bars = None
        self._status_messages = None


    def submit(self, installer: Installer):
        if installer in self._installers \
        or self._aborted:
            return

        for dep in installer.build_dependencies:
            self.submit(dep)

        self._installers.add(installer)

        # Summon rituals never have prerequisites
        if installer.summon_ritual.callback is not None:
            self._rituals[installer.summon_ritual] = set()

        if installer.install_ritual.callback is not None:
            prereqs = set()
            self._rituals[installer.install_ritual] = prereqs

            if installer.summon_ritual.callback is not None:
                prereqs.add(installer.summon_ritual)

            for dep in installer.build_dependencies:
                if dep.install_ritual.callback is not None:
                    prereqs.add(dep.install_ritual)
                elif dep.summon_ritual.callback is not None:
                    prereqs.add(dep.summon_ritual)

        self._start_pending_rituals()


    def run(
        self,
        update_freq_hz: float = 10.0,
        quiet: bool = False,
    ):

        if not quiet:
            live = self._build_rich_table(update_freq_hz)
            live.start()

        try:
            while not self._aborted:
                
                if all(
                    ritual._state in (
                        _RITUAL_STATE.COMPLETED,
                        _RITUAL_STATE.FAILED,
                    ) 
                    for ritual in self._rituals
                ):
                    break

                self._process_connections()

                if not quiet:
                    self._update_rich_table()
                
                time.sleep(1/update_freq_hz)

        except KeyboardInterrupt:
            signal.signal(signal.SIGINT, signal.SIG_IGN) # Handle this in main pulsar
            self.abort()

        finally:
            self.shutdown()
            if not quiet:
                live.stop()


    def abort(self, timeout=1.0):

        self._aborted = True

        for goblin_conn in self._worker_goblins:
            process = goblin_conn.process

            if process is not None and process.is_alive():
                process.terminate()
                process.join(timeout)

                if process.is_alive():
                    process.kill()
                    process.join()

            goblin_conn.release_ritual()

        for installer in self._installers:
            if installer.abort_ritual.callback is not None:
                installer.abort_ritual.callback()


    def shutdown(self):
        if not self._aborted and not all(
            ritual._state in (
                _RITUAL_STATE.COMPLETED,
                _RITUAL_STATE.FAILED,
            ) for ritual in self._rituals
        ):
            self.abort()

        else:
            for goblin_conn in self._worker_goblins:
                goblin_conn.release_ritual()


    def _start_pending_rituals(self):
        if self._aborted:
            return

        for goblin_conn in self._worker_goblins:

            if goblin_conn.ritual is not None \
            and goblin_conn.ritual._state == _RITUAL_STATE.RUNNING:
                continue

            for ritual, prereqs in self._rituals.items():
                if ritual._state == _RITUAL_STATE.PENDING \
                and all([   prereq._state == _RITUAL_STATE.COMPLETED
                            for prereq in prereqs]): 
                    break
            else: 
                return
    
            goblin_conn.ritual = ritual

            parent_conn, child_conn = self._ctx.Pipe(duplex=False)

            goblin_conn.goblin._callback = ritual.callback
            goblin_conn.goblin._main_thread_connection = child_conn

            goblin_conn.process = self._ctx.Process(
                target=_execute_ritual,
                args=[goblin_conn.goblin],
                name=f"Ritual-", # Name of goblin
            )
            goblin_conn.connection = parent_conn
            ritual._state = _RITUAL_STATE.RUNNING

            try: 
                goblin_conn.process.start()
                child_conn.close()

            except Exception as e:
                parent_conn.close()
                child_conn.close()

                ritual._state = _RITUAL_STATE.FAILED
                ritual.status = "Failed to start"
                ritual.error = str(e)

                self.abort()
                return


    def _process_connections(self):
        for goblin_conn in self._worker_goblins:
        
            ritual = goblin_conn.ritual

            if ritual is None or ritual._state != _RITUAL_STATE.RUNNING:
                continue

            while True:
                
                if goblin_conn.connection is None \
                or goblin_conn.ritual is None:
                    break
    
                ritual = goblin_conn.ritual
    
                try:
                    if not goblin_conn.connection.poll(0):
                        break
    
                    message = goblin_conn.connection.recv()

                except (EOFError, OSError):
                    goblin_conn.release_ritual()
                    break
    
                if 'progress' in message:
                    ritual.progress = message['progress']

                if 'status' in message:
                    ritual.status = message['status']

                if 'error' in message:
                    ritual.error = message['error']

                if 'traceback' in message:
                    ritual.traceback = message['traceback']

                if '_state' in message:
                    ritual._state = message['_state']

                    if ritual._state == _RITUAL_STATE.COMPLETED:
                        goblin_conn.release_ritual()
                        self._start_pending_rituals()

                    elif ritual._state == _RITUAL_STATE.FAILED:
                        self.abort()

            process = goblin_conn.process

            if process is None \
            or process.is_alive() \
            or ritual._state != _RITUAL_STATE.RUNNING:
                continue

            ritual._state = _RITUAL_STATE.FAILED
            ritual.status = "Worker exited unexpectedly"
            ritual.error = f"Worker exited with code {process.exitcode}"

            self.abort()
            break


    def _build_rich_table(self, update_freq_hz: float):

        from rich.table import Table
        from rich.text import Text
        from rich.progress_bar import ProgressBar
        from rich.live import Live

        from pulsar.__main__ import stderr

        self._progress_bars = dict()
        self._status_messages = dict()

        table = Table(
            "Title", "Progress Bar", "Message",
            show_header=False,
            show_edge=False,
            box=None,
        )

        for installer in self._installers:
            title = Text(installer.name)
            bar = ProgressBar(width=25)
            status = Text(
                "PENDING", 
                style='dim',
                no_wrap=True,
                overflow='crop',
            )

            self._progress_bars[installer] = bar
            self._status_messages[installer] = status

            table.add_row(title, bar, status)

        return Live(table, refresh_per_second=update_freq_hz, console=stderr)


    def _update_rich_table(self):

        for installer in self._installers:

            if installer.install_ritual.callback is None \
            or (installer.summon_ritual.callback is not None \
            and installer.summon_ritual._state != _RITUAL_STATE.COMPLETED):
                ritual = installer.summon_ritual
            else:
                ritual = installer.install_ritual

            progress_bar = self._progress_bars[installer]
            status_msg = self._status_messages[installer]

            match ritual._state:
                case _RITUAL_STATE.PENDING:
                    progress_bar.pulse = False
                    progress_bar.completed = 0.0
    
                    status_msg.plain = "PENDING"
                case _RITUAL_STATE.RUNNING:
                    progress_bar.complete_style = 'blue'
                    progress_bar.finished_style = 'blue'
                    progress_bar.pulse_style = 'blue'
                    if ritual.progress is None:
                        progress_bar.pulse = True
                    else:
                        progress_bar.pulse = False
                        progress_bar.completed = ritual.progress * 100
    
                    status_msg.plain = ritual.status
                case _RITUAL_STATE.COMPLETED:
                    progress_bar.finished_style = 'green'
                    progress_bar.pulse = False
                    progress_bar.completed = 100
    
                    status_msg.plain = "COMPLETED"
                case _RITUAL_STATE.FAILED:
                    progress_bar.style = 'red'
                    progress_bar.pulse = False
    
                    status_msg.plain = "FAILED"






## Testing

import random


# 1. Quick ritual: completes almost immediately.
quick = Installer("quick")

@quick.summon_ritual.bind
def quick_summon(goblin: SummonerGoblin):
    goblin.report_status("Performing quick operation")
    time.sleep(0.2)
    goblin.report_progress(1.0)
    goblin.report_status("Quick operation completed")

@quick.install_ritual.bind
def quick_install(goblin: SummonerGoblin):
    goblin.report_status("Performing quick operation")
    time.sleep(0.2)
    goblin.report_progress(1.0)
    goblin.report_status("Quick operation completed")

@quick.abort_ritual.bind
def quick_abort():
    print("Quick _aborted.")


# 2. Slow ritual: tests long-running workers.
slow = Installer("Slow")

@slow.summon_ritual.bind
def slow_summon(goblin: SummonerGoblin):
    for i in range(1, 21):
        time.sleep(0.5)
        goblin.report_progress(i / 20)
        goblin.report_status(f"Long operation: {i}/20")

@slow.install_ritual.bind
def slow_install(goblin: SummonerGoblin):
    for i in range(1, 21):
        time.sleep(0.5)
        goblin.report_progress(i / 20)
        goblin.report_status(f"Long operation: {i}/20")

@slow.abort_ritual.bind
def slow_abort():
    print("Slow _aborted.")


# 3. Random duration: tests unpredictable completion order.
random_duration = Installer("Random")

@random_duration.summon_ritual.bind
def random_duration_summon(goblin: SummonerGoblin):
    duration = random.uniform(1, 5)
    goblin.report_status(f"Working for {duration:.2f} seconds")
    time.sleep(duration)
    goblin.report_progress(1.0)

@random_duration.install_ritual.bind
def random_duration_install(goblin: SummonerGoblin):
    duration = random.uniform(1, 5)
    goblin.report_status(f"Working for {duration:.2f} seconds")
    time.sleep(duration)
    goblin.report_progress(1.0)

@random_duration.abort_ritual.bind
def random_duration_abort():
    print("Random duration _aborted.")


# 4. No progress: tests workers that never report progress.
silent = Installer("Silent")

@silent.summon_ritual.bind
def silent_summon(goblin: SummonerGoblin):
    goblin.report_status("Working silently")
    time.sleep(3)

@silent.abort_ritual.bind
def silent_abort():
    print("Silent _aborted.")


# 5. Status spam: tests frequent IPC messages.
status_spam = Installer("Status")

@status_spam.summon_ritual.bind
def status_spam_summon(goblin: SummonerGoblin):
    for i in range(500):
        goblin.report_status(f"Status update {i + 1}/500")

@status_spam.install_ritual.bind
def status_spam_install(goblin: SummonerGoblin):
    for i in range(500):
        goblin.report_status(f"Status update {i + 1}/500")

@status_spam.abort_ritual.bind
def status_spam_abort():
    print("Status spam _aborted.")


# 6. Progress spam: tests frequent progress messages.
progress_spam = Installer("Progress")

@progress_spam.install_ritual.bind
def progress_spam_install(goblin: SummonerGoblin):
    for i in range(1001):
        goblin.report_progress(i / 1000)

@progress_spam.abort_ritual.bind
def progress_spam_abort():
    print("Progress Spam _aborted.")


# 7. Exception immediately: tests worker exception handling.
instant_failure = Installer("Instant Failure")

@instant_failure.summon_ritual.bind
def instant_failure_ritual(goblin: SummonerGoblin):
    # raise RuntimeError("Intentional immediate failure")
    pass


# 8. Exception halfway through: tests partial progress before failure.
midway_failure = Installer(
    "Midway Failure",
    build_dependencies=set([slow])
)

@midway_failure.install_ritual.bind
def midway_failure_install(goblin: SummonerGoblin):
    for i in range(1, 6):
        time.sleep(0.5)
        goblin.report_progress(i / 10)
        goblin.report_status(f"Preparing failure: {i}/10")

    raise ValueError("Intentional halfway failure")


# 9. CPU workload: tests CPU-bound workers.
cpu_bound = Installer("CPU")

@cpu_bound.summon_ritual.bind
def cpu_bound_ritual(goblin: SummonerGoblin):
    goblin.report_status("Performing CPU-intensive calculations")

    result = 0

    for i in range(1, 5_000_001):
        result += i * i

        if i % 1_000_000 == 0:
            goblin.report_progress(i / 5_000_000)

    goblin.report_status(f"Calculation completed: {result}")


# 10. Memory allocation: tests memory-intensive workers.
memory_bound = Installer("Memory")

@memory_bound.summon_ritual.bind
def memory_bound_ritual(goblin: SummonerGoblin):
    goblin.report_status("Allocating memory")

    data = []

    for i in range(1, 11):
        data.append(bytearray(10 * 1024 * 1024))
        goblin.report_progress(i / 10)
        goblin.report_status(f"Allocated {i * 10} MB")
        time.sleep(0.2)

    goblin.report_status("Memory allocation completed")


# 11. Deterministic failure after delay.
delayed_failure = Installer("Delayed Failure")

@delayed_failure.summon_ritual.bind
def delayed_failure_ritual(goblin: SummonerGoblin):
    goblin.report_status("Starting delayed operation")
    time.sleep(5)
    # raise RuntimeError("Delayed failure triggered")


# 12. Random intermittent failures.
unstable = Installer("Unstable")

@unstable.summon_ritual.bind
def unstable_ritual(goblin: SummonerGoblin):
    for i in range(1, 11):
        time.sleep(0.4)
        goblin.report_progress(i / 10)
        goblin.report_status(f"Unstable operation: {i}/10")

        # if random.random() < 0.2:
        #     raise RuntimeError(f"Random failure at step {i}")

    goblin.report_status("Unstable operation completed")


if __name__ == '__main__':
    multiprocessing.freeze_support()

    circle = SummoningCircle(max_workers=20)

    test_installers = [
        quick,
        slow,
        random_duration,
        silent,
        status_spam,
        progress_spam,
        instant_failure,
        midway_failure,
        cpu_bound,
        memory_bound,
        delayed_failure,
        unstable,
    ]

    for installer in test_installers:
        circle.submit(installer)

    circle.run()

    print("\nTest finished.\n")


