

class Task:

    name: str
    progress: float | None
    status: str
    progress_style: str

    def __init__(
        self,
        name: str,
    ):
        self.name = name
        self.progress = None
        self.status = "Pending"
        self.progress_style = 'dim blue'