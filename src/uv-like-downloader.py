"""
UV-like Downloader - Downloads multiple files concurrently with live progress bars
"""
import time
import signal
import sys
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import requests
from rich.console import Console
from rich.live import Live
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TextColumn,
    TaskID,
)

console = Console()

# Global flag for cancellation
_cancel_flag = threading.Event()


def _signal_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) by setting the cancel flag and raising KeyboardInterrupt."""
    _cancel_flag.set()
    raise KeyboardInterrupt


# Install signal handler for Ctrl+C
signal.signal(signal.SIGINT, _signal_handler)


def download_file_task(
    url: str,
    output_path: Path,
    progress: Progress,
    task_id: TaskID,
    chunk_size: int = 8192,
) -> tuple[bool, Path, Optional[str]]:
    """
    Download a single file and update progress bar.

    Args:
        url: URL to download from
        output_path: Where to save the file
        progress: Progress instance to update
        task_id: Task ID in the progress bar
        chunk_size: Download chunk size

    Returns:
        Tuple of (success, path, error_message)
    """
    file_handle = None
    try:
        # Check if cancelled before starting
        if _cancel_flag.is_set():
            return False, output_path, "Cancelled"

        # Make the request with shorter timeout
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        # Get total file size
        total_size = int(response.headers.get("content-length", 0))
        progress.update(task_id, total=total_size)

        # Download the file in chunks
        file_handle = open(output_path, "wb")
        for chunk in response.iter_content(chunk_size=chunk_size):
            # Check cancellation flag frequently
            if _cancel_flag.is_set():
                if file_handle:
                    file_handle.close()
                return False, output_path, "Cancelled"

            if chunk:
                file_handle.write(chunk)
                progress.update(task_id, advance=len(chunk))

        file_handle.close()
        file_handle = None

        # Mark as completed
        progress.update(task_id, completed=total_size)
        return True, output_path, None

    except Exception as e:
        # Clean up file handle
        if file_handle:
            file_handle.close()
        progress.update(task_id, description=f"[red]✗ {output_path.name}")
        return False, output_path, str(e)


def download_multiple_files(
    urls: list[str],
    output_dir: Optional[str] = None,
    max_workers: int = 4,
    chunk_size: int = 8192,
) -> dict:
    """
    Download multiple files concurrently with live progress bars (uv-style).

    Args:
        urls: List of URLs to download
        output_dir: Optional directory to save files. Created if doesn't exist.
        max_workers: Maximum number of concurrent downloads
        chunk_size: Download chunk size in bytes

    Returns:
        Dictionary with 'successful', 'failed', and 'files' keys
    """
    # Setup output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path(".")

    # Create progress instance without auto-refresh
    progress = Progress(
        TextColumn("[bold blue]{task.description}", justify="left"),
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
        auto_refresh=False,
    )

    # Prepare tasks
    tasks = {}
    file_paths = {}

    for url in urls:
        # Determine filename
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        if not filename:
            filename = f"file_{len(tasks) + 1}"

        output_file = output_path / filename
        file_paths[url] = output_file

        # Add task to progress (starts with unknown total)
        task_id = progress.add_task(
            f"[cyan]⬇ {filename}",
            total=None,
            start=False,
        )
        tasks[url] = task_id

    # Track results
    successful = []
    failed = []
    executor = None

    # Clear any previous cancel flag
    _cancel_flag.clear()

    try:
        # Start downloads with live display
        with Live(progress, refresh_per_second=10, console=console):
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all download tasks
                futures = {
                    executor.submit(
                        download_file_task,
                        url,
                        file_paths[url],
                        progress,
                        tasks[url],
                        chunk_size,
                    ): url
                    for url in urls
                }

                # Start all tasks
                for url in urls:
                    progress.start_task(tasks[url])

                # Process completed downloads
                # We iterate with manual checking to allow KeyboardInterrupt
                completed_futures = set()
                while len(completed_futures) < len(futures):
                    for future in futures.keys():
                        if future in completed_futures:
                            continue

                        # Check if future is done
                        if future.done():
                            url = futures[future]
                            completed_futures.add(future)

                            try:
                                success, path, error = future.result()
                                if success:
                                    successful.append(path)
                                    progress.update(
                                        tasks[url],
                                        description=f"[green]✓ {path.name}"
                                    )
                                else:
                                    if error != "Cancelled":
                                        failed.append((url, error))
                            except Exception as e:
                                failed.append((url, str(e)))
                                progress.update(
                                    tasks[url],
                                    description=f"[red]✗ {file_paths[url].name}"
                                )

                    # Short sleep to prevent busy waiting and allow interrupt
                    time.sleep(0.1)

    except KeyboardInterrupt:
        # Set the cancel flag to stop all worker threads
        _cancel_flag.set()

        console.print("\n[yellow]⚠ Download cancelled by user[/yellow]")

        # Wait briefly for threads to finish their current chunk
        time.sleep(0.5)

        # Clean up incomplete files
        cleaned = 0
        for url, path in file_paths.items():
            if path.exists() and path not in successful:
                try:
                    path.unlink()
                    cleaned += 1
                except Exception:
                    pass

        if cleaned > 0:
            console.print(f"[dim]Cleaned up {cleaned} partial file(s)[/dim]")

        # Show what was completed before cancellation
        if successful:
            console.print(f"[dim]Completed before cancellation: {len(successful)} file(s)[/dim]")

        # Clear the flag for next time
        _cancel_flag.clear()
        raise

    # Clear the flag
    _cancel_flag.clear()

    # Print summary
    console.print()
    if successful:
        console.print(f"[bold green]✓ Downloaded {len(successful)} file(s)[/bold green]")
        for path in successful:
            console.print(f"  [green]→[/green] [cyan]{path}[/cyan]")

    if failed:
        console.print(f"\n[bold red]✗ Failed {len(failed)} file(s)[/bold red]")
        for url, error in failed:
            console.print(f"  [red]→[/red] {url}")
            console.print(f"    [dim red]{error}[/dim red]")

    return {
        "successful": successful,
        "failed": failed,
        "files": file_paths,
        "total": len(urls),
    }


def download_files_sequential(
    urls: list[str],
    output_dir: Optional[str] = None,
    chunk_size: int = 8192,
) -> dict:
    """
    Download multiple files sequentially with live progress bars.

    Similar to download_multiple_files but processes one at a time.
    Useful when you want to avoid concurrent connections.

    Args:
        urls: List of URLs to download
        output_dir: Optional directory to save files
        chunk_size: Download chunk size in bytes

    Returns:
        Dictionary with 'successful', 'failed', and 'files' keys
    """
    # Setup output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path(".")

    # Create progress instance
    progress = Progress(
        TextColumn("[bold blue]{task.description}", justify="left"),
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
        auto_refresh=False,
    )

    successful = []
    failed = []
    file_paths = {}
    current_file = None

    # Clear any previous cancel flag
    _cancel_flag.clear()

    try:
        with Live(progress, refresh_per_second=10, console=console):
            for i, url in enumerate(urls, 1):
                # Check if cancelled
                if _cancel_flag.is_set():
                    break

                # Determine filename
                parsed_url = urlparse(url)
                filename = Path(parsed_url.path).name
                if not filename:
                    filename = f"file_{i}"

                output_file = output_path / filename
                file_paths[url] = output_file
                current_file = output_file

                # Add task
                task_id = progress.add_task(
                    f"[cyan]⬇ {filename} ({i}/{len(urls)})",
                    total=None,
                )

                # Download
                success, path, error = download_file_task(
                    url, output_file, progress, task_id, chunk_size
                )

                if success:
                    successful.append(path)
                    progress.update(task_id, description=f"[green]✓ {filename}")
                    current_file = None  # Mark as completed
                else:
                    if error != "Cancelled":
                        failed.append((url, error))
                    current_file = None

    except KeyboardInterrupt:
        # Set the cancel flag
        _cancel_flag.set()
        # Clean up current incomplete file
        console.print("\n[yellow]⚠ Download cancelled by user[/yellow]")

        # Clean up incomplete files
        cleaned = 0
        for url, path in file_paths.items():
            if path.exists() and path not in successful:
                try:
                    path.unlink()
                    cleaned += 1
                except Exception:
                    pass

        if cleaned > 0:
            console.print(f"[dim]Cleaned up {cleaned} partial file(s)[/dim]")

        # Show what was completed before cancellation
        if successful:
            console.print(f"[dim]Completed before cancellation: {len(successful)} file(s)[/dim]")

        # Clear the flag for next time
        _cancel_flag.clear()
        raise

    # Clear the flag
    _cancel_flag.clear()

    # Print summary
    console.print()
    if successful:
        console.print(f"[bold green]✓ Downloaded {len(successful)} file(s)[/bold green]")
        for path in successful:
            console.print(f"  [green]→[/green] [cyan]{path}[/cyan]")

    if failed:
        console.print(f"\n[bold red]✗ Failed {len(failed)} file(s)[/bold red]")
        for url, error in failed:
            console.print(f"  [red]→[/red] {url}")
            console.print(f"    [dim red]{error}[/dim red]")

    return {
        "successful": successful,
        "failed": failed,
        "files": file_paths,
        "total": len(urls),
    }


if __name__ == "__main__":
    import sys

    # Example usage
    if len(sys.argv) < 2:
        console.print("[bold]UV-like Downloader[/bold]")
        console.print("\n[yellow]Usage:[/yellow]")
        console.print("  python uv-like-downloader.py <url1> [url2] [url3] ...")
        console.print("  python uv-like-downloader.py --dir <output_dir> <url1> [url2] ...")
        console.print("  python uv-like-downloader.py --sequential <url1> [url2] ...")
        console.print("\n[yellow]Options:[/yellow]")
        console.print("  --dir <path>       Save files to specified directory")
        console.print("  --sequential       Download files one at a time")
        console.print("  --workers <n>      Number of concurrent downloads (default: 4)")
        console.print("\n[yellow]Examples:[/yellow]")
        console.print("  python uv-like-downloader.py https://example.com/file1.zip https://example.com/file2.zip")
        console.print("  python uv-like-downloader.py --dir downloads https://example.com/file.zip")
        sys.exit(1)

    # Parse arguments
    args = sys.argv[1:]
    output_dir = None
    sequential = False
    max_workers = 4
    urls = []

    i = 0
    while i < len(args):
        if args[i] == "--dir" and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif args[i] == "--sequential":
            sequential = True
            i += 1
        elif args[i] == "--workers" and i + 1 < len(args):
            max_workers = int(args[i + 1])
            i += 2
        else:
            urls.append(args[i])
            i += 1

    if not urls:
        console.print("[red]Error: No URLs provided[/red]")
        sys.exit(1)

    # Show header
    console.print(f"[bold blue]Downloading {len(urls)} file(s)...[/bold blue]\n")

    try:
        if sequential:
            result = download_files_sequential(urls, output_dir)
        else:
            result = download_multiple_files(urls, output_dir, max_workers=max_workers)

        # Exit with appropriate code
        if result["failed"]:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Download cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)
