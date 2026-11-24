import os
import typing
import time
import pathlib
import tempfile
import threading
import shutil
import stat


class Extractor:

    archive_path: pathlib.Path
    extract_path: pathlib.Path
    stop_event: threading.Event

    CHUNK_SIZE = 64 * 1024  # 64 KB

    SUPPORTED_FORMATS = (
        '.zip',
        '.7z',
        '.tar',
        '.tar.gz',
        '.tar.xz',
    )

    def __init__(
        self,
        archive_path: pathlib.Path,
        extract_path: pathlib.Path,
    ):
        self.archive_path = pathlib.Path(archive_path)
        self.extract_path = pathlib.Path(extract_path)
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
        """Starts extraction in a separate thread."""
        with self._lock:
            if self._started:
                raise RuntimeError("Extractor has already been started")

            self._started = True

            self._thread = threading.Thread(
                target=self._extract,
                daemon=True,
            )

            self._thread.start()


    def _update_progress(self, size: int):
        with self._lock:
            self._progress += size

            now = time.monotonic()
            elapsed = now - self._last_speed_update

            if elapsed >= 0.5:
                downloaded = (
                    self._progress - self._last_speed_progress
                )

                self._speed = int(downloaded / elapsed)
                self._last_speed_progress = self._progress
                self._last_speed_update = now


    def _safe_path(self, root: pathlib.Path, name: str):
        """Validates an archive member path against path traversal."""
        name = str(name).replace("\\", "/")

        posix_path = pathlib.PurePosixPath(name)
        windows_path = pathlib.PureWindowsPath(name)

        if (
            posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or ".." in posix_path.parts
        ):
            raise ValueError(
                f"Unsafe archive path: {name}"
            )

        if not posix_path.parts:
            raise ValueError(f"Invalid archive path: {name}")

        target = root.joinpath(*posix_path.parts)

        if not target.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Unsafe archive path: {name}")

        return target


    def _write_file(self, source: typing.IO, target: pathlib.Path):
        """Writes a file while updating progress."""
        target.parent.mkdir(parents=True, exist_ok=True)

        with open(target, 'wb') as output:
            while not self.stop_event.is_set():
                chunk = source.read(self.CHUNK_SIZE)

                if not chunk:
                    break

                output.write(chunk)
                self._update_progress(len(chunk))

        if self.stop_event.is_set():
            raise InterruptedError("Extraction cancelled")


    def _extract_zip(self, root: pathlib.Path):
        import zipfile
        with zipfile.ZipFile(self.archive_path, 'r') as archive:
            infos = archive.infolist()

            total_size = 0

            for info in infos:
                if info.is_dir():
                    continue

                mode = info.external_attr >> 16

                if stat.S_ISLNK(mode):
                    raise ValueError(
                        f"Symbolic links are not supported: {info.filename}"
                    )

                total_size += info.file_size

            with self._lock:
                self._file_size = total_size

            for info in infos:
                if self.stop_event.is_set():
                    raise InterruptedError("Extraction cancelled")

                target = self._safe_path(root, info.filename)

                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                with archive.open(info, 'r') as source:
                    self._write_file(source, target)


    def _extract_tar(self, root: pathlib.Path):
        import tarfile
        with tarfile.open(self.archive_path, mode='r:*') as archive:
            members = archive.getmembers()

            total_size = 0

            for member in members:
                if member.isfile():
                    total_size += member.size
                elif not member.isdir():
                    raise ValueError(
                        f"Unsupported archive entry: {member.name}"
                    )

            with self._lock:
                self._file_size = total_size

            for member in members:
                if self.stop_event.is_set():
                    raise InterruptedError("Extraction cancelled")

                target = self._safe_path(root, member.name)

                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                if not member.isfile():
                    continue

                source = archive.extractfile(member)

                if source is None:
                    raise IOError(
                        f"Could not read archive entry: {member.name}"
                    )

                with source:
                    self._write_file(source, target)


    def _extract_7z(self, root: pathlib.Path):
        import py7zr
        from py7zr.io import WriterFactory, Py7zIO

        extractor = self

        class ProgressWriter(Py7zIO):
            def __init__(self, target):
                self.target = target
                self.file = open(target, 'wb')

            def write(self, data):
                if extractor.stop_event.is_set():
                    raise InterruptedError("Extraction cancelled")

                written = self.file.write(data)
                extractor._update_progress(written)
                return written

            def read(self, size=None):
                return self.file.read(size)

            def seek(self, offset, whence=0):
                return self.file.seek(offset, whence)

            def flush(self):
                return self.file.flush()

            def size(self):
                return self.file.tell()

            def close(self):
                self.file.close()

        class ProgressWriterFactory(WriterFactory):
            def create(self, filename):
                target = extractor._safe_path(root, filename)
                target.parent.mkdir(parents=True, exist_ok=True)

                return ProgressWriter(target)

        with py7zr.SevenZipFile(self.archive_path, mode='r') as archive:
            total_size = sum(
                getattr(info, 'uncompressed', 0) or 0
                for info in archive.list()
                if not getattr(info, 'is_directory', False)
            )

            with self._lock:
                self._file_size = total_size

            if self.stop_event.is_set():
                raise InterruptedError("Extraction cancelled")

            archive.extractall(
                path=root,
                factory=ProgressWriterFactory(),
            )

            if self.stop_event.is_set():
                raise InterruptedError("Extraction cancelled")


    def _extract(self):
        temp_path = None

        try:
            if not self.archive_path.is_file():
                raise FileNotFoundError(self.archive_path)

            if self.extract_path.exists():
                raise FileExistsError(
                    f"Destination already exists: {self.extract_path}"
                )

            suffix = self.archive_path.name.lower()

            if not any(
                suffix.endswith(ext)
                for ext in self.SUPPORTED_FORMATS
            ):
                raise ValueError(
                    f"Unsupported archive format: {suffix}"
                )

            self.extract_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temp_path = pathlib.Path(
                tempfile.mkdtemp(
                    prefix='extract_',
                    dir=self.extract_path.parent,
                )
            )

            self._start_time = time.monotonic()
            self._last_speed_update = self._start_time

            if suffix.endswith('.zip'):
                self._extract_zip(temp_path)

            elif suffix.endswith('.7z'):
                self._extract_7z(temp_path)

            elif suffix.endswith(('.tar', '.tar.gz', '.tar.xz')):
                self._extract_tar(temp_path)

            if self.stop_event.is_set():
                raise InterruptedError("Extraction cancelled")

            # Publish the extracted directory only after success.
            os.replace(temp_path, self.extract_path)
            temp_path = None

            with self._lock:
                self._finished = True
                self._speed = 0

        except Exception as exc:
            with self._lock:
                self._error = exc
                self._speed = 0

        finally:
            if temp_path is not None:
                shutil.rmtree(temp_path, ignore_errors=True)


    def get_progress(self) -> int:
        """Returns the number of bytes extracted so far."""
        with self._lock:
            return self._progress


    def get_file_size(self) -> int:
        """Returns the total uncompressed archive size in bytes."""
        with self._lock:
            return self._file_size


    def get_speed(self) -> int:
        """Returns the current extraction speed in bytes per second."""
        with self._lock:
            if self._finished or self._error is not None:
                return 0

            return self._speed


    def is_finished(self) -> bool:
        """Returns True if extraction completed successfully."""
        with self._lock:
            return self._finished


    def shutdown(self):
        """Requests cancellation and waits for the extraction thread."""
        with self._lock:
            if not self._started:
                return

            if not self._finished:
                self._cancelled = True
                self.stop_event.set()

            thread = self._thread

        if thread is not None and thread is not threading.current_thread():
            thread.join()


    def get_error(self) -> Exception | None:
        """Returns the extraction exception, if one occurred."""
        with self._lock:
            return self._error
