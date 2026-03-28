"""Download and extraction utilities."""

import gzip
import os
import shutil
import stat
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Optional
from urllib.request import urlretrieve


def download_file(url: str, dest: Path, show_progress: bool = True) -> Path:
    """
    Download a file from a URL to a destination path.

    Args:
        url: URL to download from
        dest: Destination file path
        show_progress: Whether to show download progress (unused in stdlib version)

    Returns:
        Path to the downloaded file

    Raises:
        Exception: If download fails
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if show_progress:
        print(f"Downloading {url}...")

    def _progress(block_num, block_size, total_size):
        if show_progress and total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100)
            print(f"\rProgress: {percent:.1f}%", end="", flush=True)

    urlretrieve(url, dest, reporthook=_progress if show_progress else None)

    if show_progress:
        print("\nDownload complete!")

    return dest


def extract_archive(archive_path: Path, extract_to: Path, archive_format: str) -> Path:
    """
    Extract an archive file to a directory.

    Args:
        archive_path: Path to the archive file
        extract_to: Directory to extract to
        archive_format: Format of archive ("zip", "tar.gz", "gz", "appimage")

    Returns:
        Path to the extraction directory

    Raises:
        ValueError: If archive format is unsupported
    """
    extract_to.mkdir(parents=True, exist_ok=True)

    if archive_format == "zip":
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)

    elif archive_format == "tar.gz":
        with tarfile.open(archive_path, "r:gz") as tar_ref:
            tar_ref.extractall(extract_to)

    elif archive_format == "gz":
        # For single-file gzip (like rust-analyzer)
        output_file = extract_to / archive_path.stem
        with gzip.open(archive_path, "rb") as gz_file:
            with open(output_file, "wb") as out_file:
                shutil.copyfileobj(gz_file, out_file)

    elif archive_format == "appimage":
        # AppImage is self-contained, just copy it
        output_file = extract_to / archive_path.name
        shutil.copy2(archive_path, output_file)
        # Make executable
        st = os.stat(output_file)
        os.chmod(output_file, st.st_mode | stat.S_IEXEC)

    else:
        raise ValueError(f"Unsupported archive format: {archive_format}")

    return extract_to


def download_and_extract(
    url: str,
    cache_dir: Path,
    archive_format: str,
    filename: Optional[str] = None,
    show_progress: bool = True,
) -> Path:
    """
    Download and extract an archive in one operation.

    Args:
        url: URL to download from
        cache_dir: Directory to cache downloads
        archive_format: Format of archive ("zip", "tar.gz", "gz")
        filename: Optional custom filename (otherwise derived from URL)
        show_progress: Whether to show progress

    Returns:
        Path to the extraction directory
    """
    # Determine filename
    if filename is None:
        filename = url.split("/")[-1]

    # Set up paths
    download_path = cache_dir / "downloads" / filename
    extract_path = cache_dir / "extracted" / filename.replace(".", "_")

    # Download if not cached
    if not download_path.exists():
        download_file(url, download_path, show_progress=show_progress)
    else:
        if show_progress:
            print(f"Using cached file: {download_path}")

    # Extract if not already extracted
    if not extract_path.exists():
        if show_progress:
            print(f"Extracting to {extract_path}...")
        extract_archive(download_path, extract_path, archive_format)
        if show_progress:
            print("Extraction complete!")
    else:
        if show_progress:
            print(f"Using cached extraction: {extract_path}")

    return extract_path
