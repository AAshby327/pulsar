

from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn


if __name__ == '__main__':

    import time

    job_progress = Progress(
        SpinnerColumn(),
        "{task.description}",
        BarColumn(),
    )
    job1 = job_progress.add_task("[green]Cooking")
    job2 = job_progress.add_task("[magenta]Baking", total=200)
    job3 = job_progress.add_task("[cyan]Mixing", total=400)

    with Live(job_progress, refresh_per_second=10):
        while not job_progress.finished:
            time.sleep(0.1)
            for job in job_progress.tasks:
                if not job.finished:
                    job_progress.advance(job.id)