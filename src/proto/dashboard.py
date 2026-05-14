"""
Pulsar Dashboard - Real-time system monitoring with btop-like graphs
"""
import asyncio
from datetime import datetime
from collections import deque
from typing import Deque

import psutil
try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except (ImportError, Exception):
    GPU_AVAILABLE = False

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label
from textual.reactive import reactive
from textual import events
from rich.text import Text
from rich.console import RenderableType


class SparklineWidget(Static):
    """A widget that displays a sparkline graph"""

    data: reactive[list[float]] = reactive(list, init=False)
    extra_info: reactive[str] = reactive("", init=False)
    max_points: int = 60
    label_text: str = ""
    unit: str = "%"
    color: str = "cyan"
    fixed_min: float | None = None
    fixed_max: float | None = None

    def __init__(self, label: str, unit: str = "%", color: str = "cyan", max_points: int = 60, fixed_min: float | None = None, fixed_max: float | None = None, **kwargs):
        super().__init__(**kwargs)
        self.label_text = label
        self.unit = unit
        self.color = color
        self.max_points = max_points
        self.fixed_min = fixed_min
        self.fixed_max = fixed_max
        self.data = []
        self.extra_info = ""

    def add_data_point(self, value: float):
        """Add a new data point to the sparkline"""
        self.data = list(self.data)
        self.data.append(value)
        if len(self.data) > self.max_points:
            self.data.pop(0)
        self.refresh()

    def render(self) -> RenderableType:
        """Render the sparkline graph"""
        if not self.data:
            return Text(f"{self.label_text}: No data", style=self.color)

        # Get current value and calculate max for scaling
        current_value = self.data[-1]

        # Use fixed min/max if provided, otherwise auto-scale from data
        if self.fixed_min is not None:
            min_value = self.fixed_min
        else:
            min_value = min(self.data) if self.data else 0

        if self.fixed_max is not None:
            max_value = self.fixed_max
        else:
            max_value = max(self.data) if self.data else 100

        # Sparkline characters (from lowest to highest)
        chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

        # Create label first to know its length
        label_value = f"{self.label_text}: {current_value:.1f}{self.unit}"

        # Pad the base label to fixed width for alignment
        if self.extra_info:
            # When we have extra info, don't pad (extra info has variable length)
            label_value_padded = label_value + f" {self.extra_info} "
        else:
            # Pad to fixed width when no extra info
            label_value_padded = label_value.ljust(20)

        # Calculate available width for sparkline (container width - label - padding - border)
        available_width = max(self.size.width - len(label_value_padded) - 4, 10)

        # Determine how many data points to show
        data_to_show = self.data[-available_width:] if len(self.data) > available_width else self.data

        # Build sparkline with limited points
        sparkline = ""
        for value in data_to_show:
            if max_value == min_value:
                idx = 0
            else:
                normalized = (value - min_value) / (max_value - min_value)
                idx = min(int(normalized * len(chars)), len(chars) - 1)
            sparkline += chars[idx]

        text = Text()
        text.append(label_value_padded, style=self.color)
        text.append(sparkline, style=self.color)
        text.no_wrap = True
        text.overflow = "ellipsis"

        return text


class BarGraphWidget(Static):
    """A widget that displays a horizontal bar graph"""

    value: reactive[float] = reactive(0.0)
    label_text: str = ""
    color: str = "green"
    width: int = 40

    def __init__(self, label: str, color: str = "green", width: int = 40, **kwargs):
        super().__init__(**kwargs)
        self.label_text = label
        self.color = color
        self.width = width

    def set_value(self, value: float):
        """Set the current value (0-100)"""
        self.value = max(0.0, min(100.0, value))
        self.refresh()

    def render(self) -> RenderableType:
        """Render the bar graph"""
        filled = int((self.value / 100.0) * self.width)
        empty = self.width - filled

        bar = "█" * filled + "░" * empty
        text = Text()
        text.append(f"{self.label_text}: ", style=f"bold {self.color}")
        text.append(f"{self.value:.1f}% ", style=self.color)
        text.append(bar, style=self.color)

        return text


class SystemInfoWidget(Static):
    """Widget to display system header information"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hostname = ""
        self.os_name = ""
        self.kernel = ""

    def on_mount(self):
        """Initialize system info on mount"""
        import socket
        import platform

        self.hostname = socket.gethostname()
        self.os_name = platform.system()
        self.kernel = platform.release()

    def render(self) -> RenderableType:
        """Render system info"""
        uptime_seconds = datetime.now().timestamp() - psutil.boot_time()
        hours, remainder = divmod(int(uptime_seconds), 3600)
        minutes, _ = divmod(remainder, 60)

        text = Text()
        text.append(f"{self.hostname}", style="bold #7aa2f7")
        text.append(f" • {self.os_name} {self.kernel}", style="#c0caf5")
        text.append(f" • Uptime: {hours}h {minutes}m", style="dim #565f89")

        return text


class HardwareInfoWidget(Static):
    """Widget to display hardware component information"""

    def __init__(self, info_type: str = "cpu", **kwargs):
        super().__init__(**kwargs)
        self.info_type = info_type
        self.info_text = ""

    def on_mount(self):
        """Initialize hardware info on mount"""
        import platform

        if self.info_type == "cpu":
            cpu_count = psutil.cpu_count()
            cpu_model = "Unknown"
            try:
                if platform.system() == "Linux":
                    with open("/proc/cpuinfo") as f:
                        for line in f:
                            if "model name" in line:
                                cpu_model = line.split(":")[1].strip()
                                break
                elif platform.system() == "Windows":
                    cpu_model = platform.processor()
                else:
                    cpu_model = platform.processor()
            except Exception:
                pass
            self.info_text = f"{cpu_model} ({cpu_count} cores)"

        elif self.info_type == "ram":
            total_memory = psutil.virtual_memory().total / (1024**3)  # GB
            self.info_text = f"{total_memory:.1f}GB Total"

    def set_gpu_info(self, gpu_name: str):
        """Set GPU info after initialization"""
        self.info_text = gpu_name

    def render(self) -> RenderableType:
        """Render hardware info"""
        text = Text()
        if self.info_type == "cpu":
            text.append("CPU: ", style="bold #7dcfff")
        elif self.info_type == "ram":
            text.append("RAM: ", style="bold #9ece6a")
        elif self.info_type == "gpu":
            text.append("GPU: ", style="bold #bb9af7")
        elif self.info_type == "network":
            text.append("Network: ", style="bold #bb9af7")
        elif self.info_type == "disk":
            text.append("Disk I/O: ", style="bold #73daca")
        text.append(self.info_text, style="dim #c0caf5")
        return text


class DashboardApp(App):
    """Pulsar Dashboard - Real-time system monitoring"""

    CSS = """
    Screen {
        background: #1a1b26;
    }

    Header {
        background: #24283b;
        color: #c0caf5;
        height: 1;
    }

    Footer {
        background: #24283b;
        height: 1;
    }

    #main-container {
        height: 100%;
        padding: 0 1;
    }

    #all-graphs {
        border: round #bb9af7;
        padding: 1 1;
        margin: 0;
        height: 1fr;
    }

    SparklineWidget {
        height: auto;
        padding: 0;
        margin: 0;
    }

    BarGraphWidget {
        height: auto;
        padding: 0;
        margin: 0;
    }

    SystemInfoWidget {
        height: auto;
        padding: 0;
        margin: 0 0 1 0;
    }

    HardwareInfoWidget {
        height: auto;
        padding: 0;
        margin: 0;
    }

    Label {
        height: auto;
        padding: 0;
        margin: 0;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "reset", "Reset"),
    ]

    def __init__(self):
        super().__init__()
        self.cpu_graph = None
        self.cpu_temp_graph = None
        self.cpu_core_graphs = []  # Per-core CPU graphs
        self.memory_graph = None
        self.gpu_graphs = []  # Will store (widget, gpu_index) tuples
        self.gpu_temp_graphs = []  # Will store (widget, gpu_index) tuples for temps
        self.gpu_vram_graphs = []  # Will store (widget, gpu_index) tuples for VRAM
        self.network_upload_graph = None
        self.network_download_graph = None
        self.disk_read_graph = None
        self.disk_write_graph = None
        self.update_task = None
        self.gpu_count = 0
        self.last_net_io = None
        self.last_disk_io = None
        self.last_update = None

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout"""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # All in one panel - System info and graphs
            with Vertical(id="all-graphs"):
                # System Info at the top
                yield SystemInfoWidget()

                # Separator
                yield Label("")

                # CPU Section
                yield HardwareInfoWidget(info_type="cpu")
                self.cpu_graph = SparklineWidget(
                    label="Usage",
                    unit="%",
                    color="#7dcfff",
                    max_points=50,
                    fixed_min=0.0,
                    fixed_max=100.0
                )
                yield self.cpu_graph

                self.cpu_temp_graph = SparklineWidget(
                    label="Temp",
                    unit="°C",
                    color="#f7768e",
                    max_points=50,
                    fixed_min=20.0,
                    fixed_max=100.0
                )
                yield self.cpu_temp_graph

                # Per-Core CPU Section
                cpu_count = psutil.cpu_count()
                for i in range(cpu_count):
                    core_graph = SparklineWidget(
                        label=f"Core {i}",
                        unit="%",
                        color="#7dcfff",
                        max_points=30,
                        fixed_min=0.0,
                        fixed_max=100.0
                    )
                    self.cpu_core_graphs.append(core_graph)
                    yield core_graph

                yield Label("")  # Spacer

                # Memory Section
                yield HardwareInfoWidget(info_type="ram")
                self.memory_graph = SparklineWidget(
                    label="Usage",
                    unit="%",
                    color="#9ece6a",
                    max_points=50,
                    fixed_min=0.0,
                    fixed_max=100.0
                )
                yield self.memory_graph
                yield Label("")  # Spacer

                # Network Section
                network_info = HardwareInfoWidget(info_type="network")
                network_info.info_text = "Interface Stats"
                yield network_info
                self.network_download_graph = SparklineWidget(
                    label="Download",
                    unit=" Mbps",
                    color="#9ece6a",
                    max_points=50
                )
                yield self.network_download_graph

                self.network_upload_graph = SparklineWidget(
                    label="Upload",
                    unit=" Mbps",
                    color="#e0af68",
                    max_points=50
                )
                yield self.network_upload_graph
                yield Label("")  # Spacer

                # Disk I/O Section
                disk_info = HardwareInfoWidget(info_type="disk")
                disk_info.info_text = "Read/Write Stats"
                yield disk_info
                self.disk_read_graph = SparklineWidget(
                    label="Read",
                    unit=" MB/s",
                    color="#73daca",
                    max_points=50
                )
                yield self.disk_read_graph

                self.disk_write_graph = SparklineWidget(
                    label="Write",
                    unit=" MB/s",
                    color="#ff9e64",
                    max_points=50
                )
                yield self.disk_write_graph
                yield Label("")  # Spacer

                # GPU(s) Section
                if GPU_AVAILABLE:
                    try:
                        self.gpu_count = pynvml.nvmlDeviceGetCount()
                        if self.gpu_count > 0:
                            for i in range(self.gpu_count):
                                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                                name = pynvml.nvmlDeviceGetName(handle)
                                if isinstance(name, bytes):
                                    name = name.decode('utf-8')

                                # Create GPU info widget
                                gpu_info = HardwareInfoWidget(info_type="gpu")
                                gpu_info.set_gpu_info(name)
                                yield gpu_info

                                # GPU Usage graph
                                gpu_graph = SparklineWidget(
                                    label="Usage",
                                    unit="%",
                                    color="#bb9af7",
                                    max_points=50,
                                    fixed_min=0.0,
                                    fixed_max=100.0
                                )
                                self.gpu_graphs.append((gpu_graph, i))
                                yield gpu_graph

                                # GPU Temperature graph
                                gpu_temp_graph = SparklineWidget(
                                    label="Temp",
                                    unit="°C",
                                    color="#f7768e",
                                    max_points=50,
                                    fixed_min=20.0,
                                    fixed_max=100.0
                                )
                                self.gpu_temp_graphs.append((gpu_temp_graph, i))
                                yield gpu_temp_graph

                                # GPU VRAM graph
                                gpu_vram_graph = SparklineWidget(
                                    label="VRAM",
                                    unit="%",
                                    color="#e0af68",
                                    max_points=50,
                                    fixed_min=0.0,
                                    fixed_max=100.0
                                )
                                self.gpu_vram_graphs.append((gpu_vram_graph, i))
                                yield gpu_vram_graph

                                if i < self.gpu_count - 1:  # Don't add spacer after last GPU
                                    yield Label("")
                        else:
                            yield Label("No GPUs detected")
                    except Exception as e:
                        yield Label(f"GPU monitoring unavailable: {str(e)[:40]}")
                else:
                    yield Label("GPU monitoring not available (Install pynvml)")

        yield Footer()

    async def on_mount(self) -> None:
        """Start the update loop when mounted"""
        self.update_task = asyncio.create_task(self.update_stats())

    async def update_stats(self) -> None:
        """Update statistics continuously"""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                if self.cpu_graph:
                    self.cpu_graph.add_data_point(cpu_percent)

                # CPU temperature
                if self.cpu_temp_graph:
                    try:
                        temps = psutil.sensors_temperatures()
                        # Try to find CPU temperature (different names on different systems)
                        cpu_temp = None
                        for name, entries in temps.items():
                            if 'coretemp' in name.lower() or 'cpu' in name.lower() or 'k10temp' in name.lower():
                                if entries:
                                    # Use the first entry or look for 'Package' or 'Tdie'
                                    for entry in entries:
                                        if 'package' in entry.label.lower() or 'tdie' in entry.label.lower():
                                            cpu_temp = entry.current
                                            break
                                    if cpu_temp is None:
                                        cpu_temp = entries[0].current
                                    break
                        if cpu_temp is not None:
                            self.cpu_temp_graph.add_data_point(cpu_temp)
                    except (AttributeError, Exception):
                        # sensors_temperatures not available on this system
                        pass

                # Per-core CPU usage
                if self.cpu_core_graphs:
                    try:
                        per_core_percent = psutil.cpu_percent(percpu=True, interval=0.1)
                        for i, core_graph in enumerate(self.cpu_core_graphs):
                            if i < len(per_core_percent):
                                core_graph.add_data_point(per_core_percent[i])
                    except Exception:
                        # Per-core monitoring not available
                        pass

                # Memory usage
                memory = psutil.virtual_memory()
                if self.memory_graph:
                    self.memory_graph.add_data_point(memory.percent)
                    # Calculate GB used
                    used_gb = memory.used / (1024**3)
                    self.memory_graph.extra_info = f"({used_gb:.1f}GB)"

                # Network and Disk I/O speeds
                current_net_io = psutil.net_io_counters()
                current_disk_io = psutil.disk_io_counters()
                current_time = datetime.now()

                if self.last_net_io and self.last_update:
                    time_delta = (current_time - self.last_update).total_seconds()

                    if time_delta > 0:
                        # Network speeds
                        bytes_recv_delta = current_net_io.bytes_recv - self.last_net_io.bytes_recv
                        bytes_sent_delta = current_net_io.bytes_sent - self.last_net_io.bytes_sent

                        # Convert to Mbps
                        download_speed = (bytes_recv_delta * 8) / (time_delta * 1_000_000)
                        upload_speed = (bytes_sent_delta * 8) / (time_delta * 1_000_000)

                        if self.network_download_graph:
                            self.network_download_graph.add_data_point(download_speed)

                        if self.network_upload_graph:
                            self.network_upload_graph.add_data_point(upload_speed)

                        # Disk I/O speeds (use same time_delta)
                        if current_disk_io and self.last_disk_io:
                            read_bytes_delta = current_disk_io.read_bytes - self.last_disk_io.read_bytes
                            write_bytes_delta = current_disk_io.write_bytes - self.last_disk_io.write_bytes

                            # Convert to MB/s
                            read_speed = read_bytes_delta / (time_delta * 1_000_000)
                            write_speed = write_bytes_delta / (time_delta * 1_000_000)

                            if self.disk_read_graph:
                                self.disk_read_graph.add_data_point(read_speed)

                            if self.disk_write_graph:
                                self.disk_write_graph.add_data_point(write_speed)

                self.last_net_io = current_net_io
                if current_disk_io:
                    self.last_disk_io = current_disk_io
                self.last_update = current_time

                # GPU usage, temperature, and VRAM
                if GPU_AVAILABLE and self.gpu_graphs:
                    try:
                        for gpu_graph, gpu_index in self.gpu_graphs:
                            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)

                            # GPU utilization
                            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                            gpu_graph.add_data_point(float(util.gpu))

                        # GPU temperatures
                        for gpu_temp_graph, gpu_index in self.gpu_temp_graphs:
                            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
                            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                            gpu_temp_graph.add_data_point(float(temp))

                        # GPU VRAM usage
                        for gpu_vram_graph, gpu_index in self.gpu_vram_graphs:
                            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
                            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                            vram_percent = (mem_info.used / mem_info.total) * 100
                            gpu_vram_graph.add_data_point(float(vram_percent))
                    except Exception:
                        # Silently continue on GPU errors
                        pass

                await asyncio.sleep(1)

            except Exception:
                # Don't crash the dashboard on errors
                await asyncio.sleep(1)

    def action_reset(self) -> None:
        """Reset all graphs"""
        if self.cpu_graph:
            self.cpu_graph.data = []
            self.cpu_graph.refresh()
        if self.cpu_temp_graph:
            self.cpu_temp_graph.data = []
            self.cpu_temp_graph.refresh()
        for core_graph in self.cpu_core_graphs:
            core_graph.data = []
            core_graph.refresh()
        if self.memory_graph:
            self.memory_graph.data = []
            self.memory_graph.refresh()
        if self.network_download_graph:
            self.network_download_graph.data = []
            self.network_download_graph.refresh()
        if self.network_upload_graph:
            self.network_upload_graph.data = []
            self.network_upload_graph.refresh()
        if self.disk_read_graph:
            self.disk_read_graph.data = []
            self.disk_read_graph.refresh()
        if self.disk_write_graph:
            self.disk_write_graph.data = []
            self.disk_write_graph.refresh()
        for gpu_graph, _ in self.gpu_graphs:
            gpu_graph.data = []
            gpu_graph.refresh()
        for gpu_temp_graph, _ in self.gpu_temp_graphs:
            gpu_temp_graph.data = []
            gpu_temp_graph.refresh()
        for gpu_vram_graph, _ in self.gpu_vram_graphs:
            gpu_vram_graph.data = []
            gpu_vram_graph.refresh()

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()


def run_dashboard():
    """Run the Pulsar dashboard"""
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    run_dashboard()
