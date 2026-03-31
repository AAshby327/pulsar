"""
Pulsar Downloader - Downloads files with progress tracking
"""
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from collections import deque
import requests
from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
    TextColumn,
)
from rich.text import Text
from rich.panel import Panel

console = Console()


class SpeedGraphTracker:
    """Tracks and displays a sparkline graph of download speeds."""

    # Unicode block characters for creating sparklines
    BARS = " ▁▂▃▄▅▆▇█"

    def __init__(self, console: Console, sample_interval: float = 0.5):
        self.console = console
        self.sample_interval = sample_interval  # Seconds between samples
        self.last_sample_time = 0
        self.all_speeds = []
        # Initialize with terminal width, will be updated dynamically
        self.speed_history = deque(maxlen=max(120, console.width - 2))

    def update(self, speed: float):
        """Add a new speed sample (rate-limited by sample_interval)."""
        current_time = time.time()

        # Always track for statistics
        if speed:
            self.all_speeds.append(speed)

        # Only add to graph history if enough time has passed
        if speed and (current_time - self.last_sample_time) >= self.sample_interval:
            self.speed_history.append(speed)
            self.last_sample_time = current_time

    def render(self) -> Text:
        """Render the speed graph with statistics."""
        if len(self.speed_history) < 2:
            return Text("")

        # Calculate graph width based on terminal width (minus borders)
        terminal_width = self.console.width
        graph_width = max(40, terminal_width - 2)  # Minimum 40, minus 2 for borders

        # Dynamically adjust deque size if terminal width changed
        needed_samples = max(120, graph_width)
        if self.speed_history.maxlen != needed_samples:
            # Resize the deque
            old_history = list(self.speed_history)
            self.speed_history = deque(old_history, maxlen=needed_samples)

        history = list(self.speed_history)

        # Calculate statistics first
        avg_speed = sum(self.all_speeds) / len(self.all_speeds)
        max_speed_all = max(self.all_speeds)
        min_speed_all = min(self.all_speeds)

        # Normalize speeds to 0-8 range for bar characters
        max_speed = max(history)

        # Build the output with colored bars based on speed and rounded borders
        result = Text()
        result.append("╭", style="dim blue")
        result.append("─" * graph_width, style="dim blue")
        result.append("╮", style="dim blue")
        result.append("\n")

        if max_speed == 0:
            result.append("│", style="dim blue")
            result.append("─" * graph_width, style="dim")
            result.append("│", style="dim blue")
        else:
            result.append("│", style="dim blue")

            # Render up to graph_width bars
            bars_to_render = min(len(history), graph_width)

            for i in range(bars_to_render):
                speed = history[i]
                bar_height = min(8, int((speed / max_speed) * 8))
                bar_char = self.BARS[bar_height]

                # Color based on speed relative to average
                if speed >= avg_speed * 1.2:
                    color = "bright_green"
                elif speed >= avg_speed * 0.8:
                    color = "green"
                elif speed >= avg_speed * 0.5:
                    color = "yellow"
                else:
                    color = "red"

                result.append(bar_char, style=color)

            # Pad to width if we have fewer samples than graph width
            if bars_to_render < graph_width:
                result.append(" " * (graph_width - bars_to_render), style="dim")

            result.append("│", style="dim blue")

        result.append("\n")
        result.append("╰", style="dim blue")
        result.append("─" * graph_width, style="dim blue")
        result.append("╯", style="dim blue")

        # Format speeds in MB/s
        avg_mb = avg_speed / (1024 * 1024)
        max_mb = max_speed_all / (1024 * 1024)
        min_mb = min_speed_all / (1024 * 1024)

        # Add statistics below with modern formatting
        result.append("\n")
        result.append("  ", style="dim")
        result.append("● ", style="bright_green")
        result.append(f"Peak {max_mb:5.2f} MB/s", style="bright_white")
        result.append("  ", style="dim")
        result.append("● ", style="green")
        result.append(f"Avg {avg_mb:5.2f} MB/s", style="bright_white")
        result.append("  ", style="dim")
        result.append("● ", style="yellow")
        result.append(f"Min {min_mb:5.2f} MB/s", style="bright_white")

        return result

    def get_statistics(self) -> dict:
        """Get statistics for download speeds."""
        if not self.all_speeds:
            return {}

        return {
            "avg_speed": sum(self.all_speeds) / len(self.all_speeds),
            "max_speed": max(self.all_speeds),
            "min_speed": min(self.all_speeds),
            "samples": len(self.all_speeds)
        }


def download_file(
    url: str,
    output_path: Optional[str] = None,
    chunk_size: int = 8192,
) -> Path:
    """
    Download a file from a URL with a progress bar showing download speed.

    Args:
        url: The URL to download from
        output_path: Optional path to save the file. If not provided, uses the filename from URL
        chunk_size: Size of chunks to download at a time (default 8KB)

    Returns:
        Path object pointing to the downloaded file

    Raises:
        requests.exceptions.RequestException: If download fails
        ValueError: If URL is invalid
    """
    # Parse URL and determine output filename
    if not output_path:
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        if not filename:
            filename = "downloaded_file"
        output_path = filename

    output_file = Path(output_path)

    # Make the request
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] Failed to download from {url}")
        console.print(f"[red]{str(e)}[/red]")
        raise

    # Get total file size
    total_size = int(response.headers.get("content-length", 0))

    # Create progress bar and speed graph tracker
    speed_graph = SpeedGraphTracker(console=console)

    # Create progress without auto-refresh (we'll use Live to render it)
    progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        auto_refresh=False,
        expand=False,
    )

    try:
        task = progress.add_task(
            f"[cyan]Downloading {output_file.name}",
            total=total_size
        )

        # Create a live display with progress bar and graph
        with Live(console=console, refresh_per_second=10) as live:
            # Download the file in chunks
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

                        # Update speed graph
                        task_obj = progress.tasks[0]
                        if task_obj.speed:
                            speed_graph.update(task_obj.speed)

                        # Update the live display with progress and graph
                        graph_display = speed_graph.render()
                        if graph_display.plain:  # Only show graph if there's data
                            live.update(Group(progress.get_renderable(), Text(""), graph_display))
                        else:
                            live.update(progress.get_renderable())

        # Download completed successfully - print statistics
        stats = speed_graph.get_statistics()
        console.print(f"\n[bold green]✓[/bold green] Downloaded to [cyan]{output_file}[/cyan]")

        if stats and stats.get("samples", 0) > 0:
            avg_speed = stats["avg_speed"] / (1024 * 1024)  # Convert to MB/s
            max_speed = stats["max_speed"] / (1024 * 1024)
            min_speed = stats["min_speed"] / (1024 * 1024)
            console.print(
                f"[dim]Stats: Avg: {avg_speed:.2f} MB/s  "
                f"Max: {max_speed:.2f} MB/s  "
                f"Min: {min_speed:.2f} MB/s[/dim]"
            )

        return output_file

    except KeyboardInterrupt:
        # Delete the partial file
        if output_file.exists():
            output_file.unlink()

        # Print cancellation message with statistics
        console.print(f"\n[yellow]⚠ Download cancelled by user[/yellow]")
        console.print(f"[dim]Partial file deleted: {output_file.name}[/dim]")

        # Show statistics if we have any
        stats = speed_graph.get_statistics()
        if stats and stats.get("samples", 0) > 0:
            avg_speed = stats["avg_speed"] / (1024 * 1024)
            max_speed = stats["max_speed"] / (1024 * 1024)
            console.print(
                f"[dim]Stats before cancellation: Avg: {avg_speed:.2f} MB/s  "
                f"Max: {max_speed:.2f} MB/s[/dim]"
            )

        raise


def download_multiple_files(urls: list[str], output_dir: Optional[str] = None) -> list[Path]:
    """
    Download multiple files from a list of URLs.

    Args:
        urls: List of URLs to download
        output_dir: Optional directory to save files. Created if it doesn't exist.

    Returns:
        List of Path objects pointing to downloaded files
    """
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path(".")

    downloaded_files = []

    for i, url in enumerate(urls, 1):
        console.print(f"\n[bold]File {i}/{len(urls)}[/bold]")

        # Get filename from URL
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        if not filename:
            filename = f"file_{i}"

        output_file = output_path / filename

        try:
            downloaded_file = download_file(url, str(output_file))
            downloaded_files.append(downloaded_file)
        except KeyboardInterrupt:
            console.print(f"\n[yellow]Batch download cancelled by user[/yellow]")
            raise
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Skipped {url}: {str(e)}\n")
            continue

    console.print(f"\n[bold green]Downloaded {len(downloaded_files)}/{len(urls)} files[/bold green]")
    return downloaded_files


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] python downloader.py <url> [output_path]")
        console.print("[yellow]Example:[/yellow] python downloader.py https://example.com/file.zip")
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        download_file(url, output)
    except KeyboardInterrupt:
        # Already handled in download_file, just exit cleanly
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        console.print(f"\n[bold red]Download failed:[/bold red] {str(e)}")
        sys.exit(1)
