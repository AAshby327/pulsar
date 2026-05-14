import rich.progress_bar
import rich.console
import time

console = rich.console.Console()
bar = rich.progress_bar.ProgressBar(width=50, total=100)
bar.pulse = True
console.show_cursor(False)
for n in range(0, 101, 1):
    bar.update(n)
    console.print(bar)
    console.print('\r')
    time.sleep(0.05)
console.show_cursor(True)
console.print()