import typing
import enum
import signal
import time
import traceback
import multiprocessing

if typing.TYPE_CHECKING:
    from multiprocessing.context import SpawnProcess, SpawnContext
    from multiprocessing.connection import PipeConnection

    DECORATOR_INPUT = typing.TypeVar('DECORATOR_INPUT', bound=typing.Callable)


class SummonerGoblin:

    callback: typing.Callable[[SummonerGoblin], None]
    connection: PipeConnection

    def __init__(
        self, 
        callback: typing.Callable[[SummonerGoblin], None],
        connection: PipeConnection,
    ):
        self.callback = callback
        self.connection = connection

    def report_progress(self, progress: float | None):
        self.connection.send({'progress': progress})

    def report_status(self, status: str):
        self.connection.send({'status': status})


def _execute_ritual(goblin: SummonerGoblin):
    # Prevent Ctrl+C from generating worker tracebacks.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        goblin.connection.send({'state': Ritual.RITUAL_STATE.RUNNING})
        goblin.callback(goblin)
        goblin.connection.send({'state': Ritual.RITUAL_STATE.COMPLETED})

    except BaseException as e:
        try:
            goblin.connection.send({
                'state': Ritual.RITUAL_STATE.FAILED,
                'error': f'{type(e).__name__}: {e}',
                'traceback': traceback.format_exc(),
            })

        except (BrokenPipeError, EOFError, OSError):
            pass

    finally:
        goblin.connection.close()


class Ritual:
    callback: typing.Callable[[SummonerGoblin], None] | None

    state: RITUAL_STATE
    progress: float | None
    status: str

    process: SpawnProcess | None
    connection: PipeConnection | None

    error: str | None
    traceback: str | None

    class RITUAL_STATE(enum.Enum):
        PENDING = enum.auto()
        RUNNING = enum.auto()
        COMPLETED = enum.auto()
        FAILED = enum.auto()
        ABORTED = enum.auto()


    def __init__(self, callback: typing.Callable[[Ritual], None] | None = None):
        self.callback = callback

        self.state = Ritual.RITUAL_STATE.PENDING
        self.progress = None
        self.status = ''

        self.process = None
        self.connection = None

        self.error = None
        self.traceback = None


    def bind(self, callback: DECORATOR_INPUT) -> DECORATOR_INPUT:
        self.callback = callback
        return callback


    def _reset(self):
        self.__init__(self.callback)


class Installer:

    build_dependencies: set[Installer]

    summon_ritual: Ritual
    install_ritual: Ritual
    abort_ritual: Ritual

    def __init__(self, build_dependencies: set[Installer] | None = None):
        self.build_dependencies = build_dependencies \
                if build_dependencies is not None else set()

        self.summon_ritual = Ritual()
        self.install_ritual = Ritual()
        self.abort_ritual = Ritual()


class SummoningCircle:

    ctx: SpawnContext

    max_workers: int

    installers: set[Installer]
    rituals: set[Ritual]
    pending_rituals: set[Ritual]


    def __init__(self, max_workers=multiprocessing.cpu_count()):

        assert max_workers >= 1

        self.ctx = multiprocessing.get_context('spawn')
        self.max_workers = max_workers
        self.installers = set()
        self.rituals = set()
        self.pending_rituals = set()


    def submit(self, installer: Installer): 
        if installer in self.installers:
            return

        self.installers.add(installer)

        self.rituals.add(installer.summon_ritual)
        self.pending_rituals.add(installer.summon_ritual)

        for dep in installer.build_dependencies:
            self.submit(dep)

        self._start_pending_rituals()


    def run(self):
        try:
            while not all(
                ritual.state in (
                    Ritual.RITUAL_STATE.COMPLETED,
                    Ritual.RITUAL_STATE.FAILED,
                    Ritual.RITUAL_STATE.ABORTED,
                ) for ritual in self.rituals
            ):
                for ritual in self.rituals:

                    if ritual.state != Ritual.RITUAL_STATE.RUNNING:
                        continue

                    self._process_connection(ritual)

                    if ritual.process is None \
                    or ritual.process.is_alive() \
                    or ritual.state != Ritual.RITUAL_STATE.RUNNING:
                        continue

                    ritual.state = Ritual.RITUAL_STATE.FAILED
                    ritual.status = "Worker exited unexpectedly"
                    ritual.error = f"Worker exited with code {ritual.process.exitcode}"

                    self._cleanup_ritual(ritual)
                    self._start_pending_rituals()

                for ritual in self.rituals:
                    print(ritual.state, ritual.progress, ritual.status)
                print("\n\n\n")

                time.sleep(0.5) # Make this a param

        except KeyboardInterrupt:
            signal.signal(signal.SIGINT, signal.SIG_IGN) # Handle this in main pulsar
            self.abort()

        finally:
            self.shutdown()


    def abort(self, timeout=1.0):
        for ritual in self.rituals:

            if ritual.state in (
                Ritual.RITUAL_STATE.COMPLETED,
                Ritual.RITUAL_STATE.FAILED,
                Ritual.RITUAL_STATE.ABORTED,
            ):
                continue

            if ritual.state == Ritual.RITUAL_STATE.PENDING:
                ritual.state = Ritual.RITUAL_STATE.ABORTED
                continue

            if ritual.process is not None and ritual.process.is_alive():

                ritual.process.terminate()
                ritual.process.join(timeout)

                if ritual.process.is_alive():
                    ritual.process.kill()
                    ritual.process.join()

            self._cleanup_ritual(ritual)

            ritual.state = Ritual.RITUAL_STATE.ABORTED


    def shutdown(self):

        if not all(
            ritual.state in (
                Ritual.RITUAL_STATE.COMPLETED,
                Ritual.RITUAL_STATE.FAILED,
                Ritual.RITUAL_STATE.ABORTED,
            ) for ritual in self.rituals
        ):
            self.abort()

        for ritual in self.rituals:
            self._cleanup_ritual(ritual)


    def _start_pending_rituals(self):

        running = sum(
            ritual.state == Ritual.RITUAL_STATE.RUNNING
            for ritual in self.rituals
        )

        while running < self.max_workers and len(self.pending_rituals) > 0:
            ritual = self.pending_rituals.pop()

            parent_conn, child_conn = self.ctx.Pipe(duplex=False)

            worker_goblin = SummonerGoblin(
                ritual.callback,
                child_conn,
            )

            process = self.ctx.Process(
                target=_execute_ritual,
                args=(worker_goblin,),
                name=f"Ritual-",
            )

            try:
                process.start()
                child_conn.close()

            except Exception as e:
                parent_conn.close()
                child_conn.close()

                ritual.state = Ritual.RITUAL_STATE.FAILED
                ritual.status = 'Failed to start'
                ritual.error = str(e)

                continue

            ritual.process = process
            ritual.connection = parent_conn
            ritual.state = Ritual.RITUAL_STATE.RUNNING

            running += 1


    def _process_connection(self, ritual: Ritual):
        while True:

            if ritual.connection is None:
                return

            try:
                if not ritual.connection.poll(0):
                    break

                message = ritual.connection.recv()

                if 'progress' in message:
                    ritual.progress = message['progress']

                if 'status' in message:
                    ritual.status = message['status']

                if 'error' in message:
                    ritual.error = message['error']

                if 'traceback' in message:
                    ritual.traceback = message['traceback']

                if 'state' in message:
                    ritual.state = message['state']

                    if ritual.state in (
                        Ritual.RITUAL_STATE.COMPLETED,
                        Ritual.RITUAL_STATE.FAILED,
                        Ritual.RITUAL_STATE.ABORTED,
                    ):
                        self._cleanup_ritual(ritual)
                        self._start_pending_rituals()

            except (EOFError, OSError):
                self._cleanup_ritual(ritual)
                # No cleanup process in original
                break


    def _cleanup_ritual(self, ritual: Ritual):
        if ritual.connection is not None:
            try:
                ritual.connection.close()
            except OSError:
                pass

            ritual.connection = None


        if ritual.process is not None:
            if ritual.process.is_alive():
                ritual.process.join(1.0)

            if not ritual.process.is_alive():
                ritual.process.join()

                try:
                    ritual.process.close()
                except (ValueError, OSError):
                    pass

            ritual.process = None





















## Testing

import random


# 1. Quick ritual: completes almost immediately.
quick = Installer()

@quick.summon_ritual.bind
def quick_ritual(goblin: SummonerGoblin):
    goblin.report_status("Performing quick operation")
    time.sleep(0.2)
    goblin.report_progress(1.0)
    goblin.report_status("Quick operation completed")


# 2. Slow ritual: tests long-running workers.
slow = Installer()

@slow.summon_ritual.bind
def slow_ritual(goblin: SummonerGoblin):
    for i in range(1, 21):
        time.sleep(0.5)
        goblin.report_progress(i / 20)
        goblin.report_status(f"Long operation: {i}/20")


# 3. Random duration: tests unpredictable completion order.
random_duration = Installer()

@random_duration.summon_ritual.bind
def random_duration_ritual(goblin: SummonerGoblin):
    duration = random.uniform(1, 5)
    goblin.report_status(f"Working for {duration:.2f} seconds")
    time.sleep(duration)
    goblin.report_progress(1.0)


# 4. No progress: tests workers that never report progress.
silent = Installer()

@silent.summon_ritual.bind
def silent_ritual(goblin: SummonerGoblin):
    goblin.report_status("Working silently")
    time.sleep(3)


# 5. Status spam: tests frequent IPC messages.
status_spam = Installer()

@status_spam.summon_ritual.bind
def status_spam_ritual(goblin: SummonerGoblin):
    for i in range(500):
        goblin.report_status(f"Status update {i + 1}/500")


# 6. Progress spam: tests frequent progress messages.
progress_spam = Installer()

@progress_spam.summon_ritual.bind
def progress_spam_ritual(goblin: SummonerGoblin):
    for i in range(1001):
        goblin.report_progress(i / 1000)


# 7. Exception immediately: tests worker exception handling.
instant_failure = Installer()

@instant_failure.summon_ritual.bind
def instant_failure_ritual(goblin: SummonerGoblin):
    raise RuntimeError("Intentional immediate failure")


# 8. Exception halfway through: tests partial progress before failure.
midway_failure = Installer()

@midway_failure.summon_ritual.bind
def midway_failure_ritual(goblin: SummonerGoblin):
    for i in range(1, 6):
        time.sleep(0.5)
        goblin.report_progress(i / 10)
        goblin.report_status(f"Preparing failure: {i}/10")

    raise ValueError("Intentional halfway failure")


# 9. CPU workload: tests CPU-bound workers.
cpu_bound = Installer()

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
memory_bound = Installer()

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
delayed_failure = Installer()

@delayed_failure.summon_ritual.bind
def delayed_failure_ritual(goblin: SummonerGoblin):
    goblin.report_status("Starting delayed operation")
    time.sleep(5)
    raise RuntimeError("Delayed failure triggered")


# 12. Random intermittent failures.
unstable = Installer()

@unstable.summon_ritual.bind
def unstable_ritual(goblin: SummonerGoblin):
    for i in range(1, 11):
        time.sleep(0.4)
        goblin.report_progress(i / 10)
        goblin.report_status(f"Unstable operation: {i}/10")

        if random.random() < 0.2:
            raise RuntimeError(f"Random failure at step {i}")

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

    print("\nAll tasks finished.\n")


