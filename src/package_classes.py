import os

import abc
import typing
import logging
import urllib.request
from pathlib import Path

from rich.progress import Progress, DownloadColumn, BarColumn, TransferSpeedColumn, TimeRemainingColumn

import pulsar_env

class LastLogHandler(logging.Handler):
    """Handler that stores the most recent log record."""
    def __init__(self):
        super().__init__()
        self.last_record = None

    def emit(self, record):
        self.last_record = record

class _PulsarPackage(abc.ABC):

    PACKAGE_LIST: dict[str, '_PulsarPackage'] = None
    CACHE_DIR: Path = None

    name: str = ''
    description: str = ''
    dependencies: list['_PulsarPackage'] = []

    status: str = ''
    status_style: str = ''

    download_progress: Progress | None = None
    logger: logging.Logger = None

    @classmethod
    @abc.abstractmethod
    def is_installed(cls) -> bool:
        raise NotImplementedError()
    
    @classmethod
    @abc.abstractmethod
    def is_installed_with_pulsar(cls) -> bool:
        raise NotImplementedError()
    
    @classmethod
    @abc.abstractmethod
    def get_version(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def on_env_activate(cls):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def install(
            cls, 
            version: typing.Optional[str] = None, 
            reinstall: bool = False,
            refresh_cache: bool = False,
    ):
        raise NotImplementedError()
    
    @classmethod
    @abc.abstractmethod
    def uninstall(cls): 
        raise NotImplementedError()
    
    def __init_subclass__(cls):

        if not cls.name:
            cls.name = cls.__name__

        cls.CACHE_DIR = Path(os.path.join(pulsar_env.PULSAR_CACHE_DIR, cls.name))

        if 'logger' in cls.__dict__ and cls.logger is not None:
            raise ValueError("Do not set logger in subclass.")
        
        cls.logger = logging.getLogger(f'pulsar.packages.{cls.name}')
        cls.logger.setLevel(logging.INFO)
        handler = LastLogHandler()
        cls.logger.addHandler(handler)
        
        if cls.PACKAGE_LIST is not None:
            assert cls.name not in cls.PACKAGE_LIST
            cls.PACKAGE_LIST[cls.name] = cls
        
        return super().__init_subclass__()
    
    @classmethod
    def set_status(cls, status: str, style: str | None = None):
        cls.status = status
        cls.status_style = style if style else ''

    @classmethod
    def download(cls, url: str, destination: str | Path, chunk_size: int = 8192) -> Path:
        """
        Download a file from a URL and track progress.

        Args:
            url: The URL to download from
            destination: Path where the file should be saved
            chunk_size: Size of chunks to download (default 8192 bytes)

        Returns:
            Path to the downloaded file
        """
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Create progress bar
        cls.download_progress = Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        )

        try:
            # Open the URL
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('content-length', 0))

                # Add download task
                task_id = cls.download_progress.add_task(
                    f"Downloading {destination.name}",
                    total=total_size
                )

                # Download and write in chunks
                with open(destination, 'wb') as file:
                    downloaded = 0
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        file.write(chunk)
                        downloaded += len(chunk)
                        cls.download_progress.update(task_id, advance=len(chunk))

                cls.logger.info(f"Downloaded {destination.name} ({downloaded} bytes)")

        finally:
            # Clean up progress bar
            cls.download_progress = None

        return destination


class LinuxPackage(_PulsarPackage):
    
    dependencies: list['LinuxPackage']
    PACKAGE_LIST: dict[str, 'LinuxPackage'] = dict()

class WindowsPackage(_PulsarPackage):

    dependencies: list['WindowsPackage']
    PACKAGE_LIST: dict[str, 'WindowsPackage'] = dict()
