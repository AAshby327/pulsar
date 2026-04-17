#!/usr/bin/env python3
"""
Interactive checkbox list using rich library with keyboard navigation.
Install with: pip install rich

Navigation:
- Arrow keys (↑/↓) or hjkl to move
- Tab or Space to toggle selection
- Enter to confirm
- q to quit without selecting
"""

import sys
import tty
import termios
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

console = Console()


def get_key():
    """Read a single keypress from the terminal."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        # Handle escape sequences for arrow keys
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                return f'\x1b[{ch3}'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def create_display(options, current_idx, selected_indices, title):
    """Create the display table."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("", style="", width=3)
    table.add_column("", style="", width=None)

    for idx, option in enumerate(options):
        # Checkbox symbol
        if idx in selected_indices:
            checkbox = r"\[x]"
        else:
            checkbox = r"\[ ]"

        # Highlight current row
        if idx == current_idx:
            option_text = f"[black on white]{option}[/black on white]"
            checkbox = f"[black on white]{checkbox}[/black on white]"
        else:
            option_text = option

        table.add_row(checkbox, option_text)

    # Create panel with instructions
    panel = Panel(
        table,
        title=f"[bold blue]{title}[/bold blue]",
        subtitle=(
            f"[dim]Selected: {len(selected_indices)} | "
            f"↑↓/hjkl:move | Tab/Space:toggle | Enter:confirm | q:quit[/dim]"
        ),
        border_style="blue"
    )

    return panel


def interactive_checkbox_menu(options, title="Select Options"):
    """
    Interactive checkbox menu with arrow key navigation.
    Returns a list of selected options.
    """
    current_idx = 0
    selected_indices = set()

    with Live(create_display(options, current_idx, selected_indices, title),
              console=console, refresh_per_second=4, auto_refresh=False) as live:

        while True:
            key = get_key()

            # Navigation: Arrow down or j
            if key in ['\x1b[B', 'j']:
                current_idx = (current_idx + 1) % len(options)

            # Navigation: Arrow up or k
            elif key in ['\x1b[A', 'k']:
                current_idx = (current_idx - 1) % len(options)

            # Navigate down with l or arrow right
            elif key in ['l', '\x1b[C']:
                current_idx = (current_idx + 1) % len(options)

            # Navigate up with h or arrow left
            elif key in ['h', '\x1b[D']:
                current_idx = (current_idx - 1) % len(options)

            # Toggle selection: Tab or Space
            elif key in ['\t', ' ']:
                if current_idx in selected_indices:
                    selected_indices.remove(current_idx)
                else:
                    selected_indices.add(current_idx)

            # Confirm: Enter
            elif key in ['\r', '\n']:
                break

            # Quit: q or Ctrl+C
            elif key in ['q', '\x03']:
                selected_indices.clear()
                break

            # Update display
            live.update(create_display(options, current_idx, selected_indices, title))
            live.refresh()

    return [options[i] for i in sorted(selected_indices)]


def main():
    # Define options
    options = [
        'Python',
        'JavaScript',
        'Java',
        'C++',
        'Go',
        'Rust',
        'Ruby',
        'TypeScript',
    ]

    console.print("\n[bold cyan]Interactive Checkbox Selection[/bold cyan]\n")

    try:
        selected = interactive_checkbox_menu(options, "Select Programming Languages")

        # Display results
        console.print("\n" + "="*50)
        if selected:
            console.print(f"[bold green]✓ You selected {len(selected)} language(s):[/bold green]")
            for lang in selected:
                console.print(f"  • [cyan]{lang}[/cyan]")
        else:
            console.print("[yellow]No languages selected.[/yellow]")
        console.print("="*50)

    except KeyboardInterrupt:
        console.print("\n[yellow]Selection cancelled.[/yellow]")


if __name__ == "__main__":
    main()
