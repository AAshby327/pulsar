import pathlib
import threading
import time
import urllib.request


class Downloader:

    url: str
    file_path: pathlib.Path
    stop_event: threading.Event

    CHUNK_SIZE = 64 * 1024  # 64 KB

    def __init__(self, url: str, file_path: pathlib.Path):
        self.url = url
        self.file_path = pathlib.Path(file_path)
        self.stop_event = threading.Event()

        self._progress = 0
        self._file_size = 0
        self._speed = 0

        self._finished = False
        self._cancelled = False
        self._started = False
        self._error = None
        self._lock = threading.Lock()
        
        self._thread = None

        self._start_time = None
        self._last_speed_update = None
        self._last_speed_progress = 0


    def start(self):
        """Starts the download in a separate thread."""
        with self._lock:
            if self._started:
                raise RuntimeError("Downloader has already been started")

            self._started = True
            self._thread = threading.Thread(
                target=self._download,
                daemon=True
            )
            self._thread.start()


    def _download(self):
        temp_path = self.file_path.with_name(
            self.file_path.name + ".part"
        )

        try:
            self.file_path.parent.mkdir(
                parents=True, exist_ok=True
            )

            request = urllib.request.Request(
                self.url,
                headers={'User-Agent': 'Python Downloader'}
            )

            with urllib.request.urlopen(request, timeout=15) as response:
                content_length = response.headers.get('Content-Length')

                with self._lock:
                    self._file_size = (
                        int(content_length)
                        if content_length is not None
                        else 0
                    )

                self._start_time = time.monotonic()
                self._last_speed_update = self._start_time

                with open(temp_path, 'wb') as file:
                    while not self.stop_event.is_set():
                        chunk = response.read(self.CHUNK_SIZE)

                        if not chunk:
                            break

                        file.write(chunk)

                        with self._lock:
                            self._progress += len(chunk)

                            now = time.monotonic()
                            elapsed = now - self._last_speed_update

                            if elapsed >= 0.5:
                                downloaded = (
                                    self._progress -
                                    self._last_speed_progress
                                )

                                self._speed = int(downloaded / elapsed)
                                self._last_speed_progress = self._progress
                                self._last_speed_update = now

                    file.flush()

                if self.stop_event.is_set():
                    return

                if (
                    self._file_size > 0
                    and self._progress != self._file_size
                ):
                    raise IOError(
                        f"Incomplete download: "
                        f"{self._progress}/{self._file_size} bytes"
                    )

                temp_path.replace(self.file_path)

                with self._lock:
                    self._finished = True
                    self._speed = 0

        except Exception as exc:
            with self._lock:
                self._error = exc
                self._speed = 0

        finally:
            if self.stop_event.is_set() or self._error is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass


    def get_progress(self) -> int:
        """Returns the number of bytes downloaded."""
        with self._lock:
            return self._progress


    def get_file_size(self) -> int:
        """Returns the total file size in bytes, or 0 if unknown."""
        with self._lock:
            return self._file_size


    def get_speed(self) -> int:
        """Returns the current download speed in bytes per second."""
        with self._lock:
            if self._finished or self._error is not None:
                return 0

            return self._speed


    def is_finished(self) -> bool:
        """Returns True if the download completed successfully."""
        with self._lock:
            return self._finished


    def shutdown(self):
        """Requests cancellation and waits for the worker thread."""
        with self._lock:
            if not self._started:
                return

            if self._finished:
                thread = self._thread
            else:
                self._cancelled = True
                self.stop_event.set()
                thread = self._thread

        if thread is not None and thread is not threading.current_thread():
            thread.join()


    def get_error(self) -> Exception | None:
        """Returns the download exception, if one occurred."""
        with self._lock:
            return self._error



