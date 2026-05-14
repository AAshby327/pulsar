#!/usr/bin/env python3
"""Simple star animation using Rich library."""

import random
import time
from rich.console import Console
from rich.live import Live
from rich.text import Text

def main():
    console = Console()
    width = console.width
    height = console.height - 2

    # Create stars at random positions
    stars = []
    for _ in range(100):
        stars.append({
            'x': random.randint(0, width - 1),
            'y': random.randint(0, height - 1),
            'speed': random.uniform(0.5, 2.0),
            'char': random.choice(['*', '·', '✦', '✧'])
        })

    with Live(console=console, refresh_per_second=20, screen=True) as live:
        try:
            while True:
                # Create a blank screen
                lines = [[' ' for _ in range(width)] for _ in range(height)]

                # Update star positions
                for star in stars:
                    star['x'] -= star['speed']

                    # Wrap around when star goes off screen
                    if star['x'] < 0:
                        star['x'] = width - 1
                        star['y'] = random.randint(0, height - 1)

                    # Place star on screen
                    x, y = int(star['x']), int(star['y'])
                    if 0 <= x < width and 0 <= y < height:
                        lines[y][x] = star['char']

                # Build output text
                text = Text()
                for line in lines:
                    text.append(''.join(line) + '\n', style='white')

                live.update(text)
                time.sleep(0.05)

        except KeyboardInterrupt:
            console.clear()
            console.print("\n[yellow]Animation stopped![/yellow]")

if __name__ == '__main__':
    main()
