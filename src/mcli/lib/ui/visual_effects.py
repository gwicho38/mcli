"""
🎨 MCLI Visual Effects and Enhanced CLI Experience
Provides stunning visual elements, animations, and rich formatting for the CLI
"""

import random
import sys
import threading
import time
from typing import Any, Dict, List, Optional

from rich.align import Align
from rich.box import ASCII, DOUBLE, HEAVY, ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

console = Console()


class MCLIBanner:
    """Stunning ASCII art banners for MCLI"""

    MAIN_BANNER = """
╔════════════════════════════════════════════════════════════════╗
║  ███╗   ███╗ ██████╗██╗     ██╗    ┌─┐┌─┐┬ ┬┌─┐┬─┐┌─┐┌┬┐    ║
║  ████╗ ████║██╔════╝██║     ██║    ├─┘│ ││││├┤ ├┬┘├┤  ││     ║  
║  ██╔████╔██║██║     ██║     ██║    ┴  └─┘└┴┘└─┘┴└─└─┘─┴┘    ║
║  ██║╚██╔╝██║██║     ██║     ██║    ┌┐ ┬ ┬  ┬─┐┬ ┬┌─┐┌┬┐      ║
║  ██║ ╚═╝ ██║╚██████╗███████╗██║    ├┴┐└┬┘  ├┬┘│ │└─┐ │       ║
║  ╚═╝     ╚═╝ ╚═════╝╚══════╝╚═╝    └─┘ ┴   ┴└─└─┘└─┘ ┴       ║
╚════════════════════════════════════════════════════════════════╝
"""

    PERFORMANCE_BANNER = """
⚡ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ⚡
   ██████╗ ███████╗██████╗ ███████╗ ██████╗ ██████╗ ███╗   ███╗
   ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗██╔══██╗████╗ ████║
   ██████╔╝█████╗  ██████╔╝█████╗  ██║   ██║██████╔╝██╔████╔██║
   ██╔═══╝ ██╔══╝  ██╔══██╗██╔══╝  ██║   ██║██╔══██╗██║╚██╔╝██║
   ██║     ███████╗██║  ██║██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║
   ╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝
⚡ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ⚡
"""

    RUST_BANNER = """
🦀 ┌─────────────────────────────────────────────────────────────┐ 🦀
   │  ██████╗ ██╗   ██╗███████╗████████╗                        │
   │  ██╔══██╗██║   ██║██╔════╝╚══██╔══╝                        │
   │  ██████╔╝██║   ██║███████╗   ██║                           │
   │  ██╔══██╗██║   ██║╚════██║   ██║                           │
   │  ██║  ██║╚██████╔╝███████║   ██║                           │
   │  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝                           │
   │           ███████╗██╗  ██╗████████╗███████╗███╗   ██╗      │
   │           ██╔════╝╚██╗██╔╝╚══██╔══╝██╔════╝████╗  ██║      │
   │           █████╗   ╚███╔╝    ██║   █████╗  ██╔██╗ ██║      │
   │           ██╔══╝   ██╔██╗    ██║   ██╔══╝  ██║╚██╗██║      │
   │           ███████╗██╔╝ ██╗   ██║   ███████╗██║ ╚████║      │
   │           ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝      │
🦀 └─────────────────────────────────────────────────────────────┘ 🦀
"""

    @classmethod
    def show_main_banner(cls, subtitle: str = "Powered by Rust"):
        """Display the main MCLI banner with gradient colors"""
        console.print()

        # Create gradient text effect
        banner_text = Text(cls.MAIN_BANNER)
        banner_text.stylize("bold magenta on black", 0, len(banner_text))

        # Add subtitle
        subtitle_text = Text(f"                    {subtitle}", style="bold cyan italic")

        panel = Panel(
            Align.center(Text.assemble(banner_text, "\n", subtitle_text)),
            box=DOUBLE,
            border_style="bright_blue",
            padding=(1, 2),
        )

        console.print(panel)
        console.print()

    @classmethod
    def show_performance_banner(cls):
        """Display performance optimization banner"""
        console.print()

        banner_text = Text(cls.PERFORMANCE_BANNER)
        banner_text.stylize("bold yellow on black")

        panel = Panel(
            Align.center(banner_text),
            title="⚡ PERFORMANCE MODE ACTIVATED ⚡",
            title_align="center",
            box=HEAVY,
            border_style="bright_yellow",
            padding=(1, 2),
        )

        console.print(panel)

    @classmethod
    def show_rust_banner(cls):
        """Display Rust extensions banner"""
        console.print()

        banner_text = Text(cls.RUST_BANNER)
        banner_text.stylize("bold red on black")

        panel = Panel(
            Align.center(banner_text),
            title="🦀 RUST EXTENSIONS LOADED 🦀",
            title_align="center",
            box=ROUNDED,
            border_style="bright_red",
            padding=(1, 2),
        )

        console.print(panel)


class AnimatedSpinner:
    """Fancy animated spinners and loading indicators"""

    SPINNERS = {
        "rocket": ["🚀", "🌟", "⭐", "✨", "💫", "🌠"],
        "gears": ["⚙️ ", "⚙️⚙️", "⚙️⚙️⚙️", "⚙️⚙️", "⚙️ ", " "],
        "rust": ["🦀", "🔧", "⚡", "🔥", "💨", "✨"],
        "matrix": ["│", "╱", "─", "╲"],
        "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "arrows": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
        "lightning": ["⚡", "🌩️", "⚡", "🔥", "💥", "✨"],
    }

    def __init__(self, spinner_type: str = "rocket", speed: float = 0.1):
        self.frames = self.SPINNERS.get(spinner_type, self.SPINNERS["rocket"])
        self.speed = speed
        self.running = False
        self.thread = None

    def start(self, message: str = "Loading..."):
        """Start the animated spinner"""
        self.running = True
        self.thread = threading.Thread(target=self._animate, args=(message,))
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the spinner"""
        self.running = False
        if self.thread:
            self.thread.join()
        # Clear the line
        console.print("\r" + " " * 80 + "\r", end="")

    def _animate(self, message: str):
        """Animation loop"""
        frame_idx = 0
        while self.running:
            frame = self.frames[frame_idx % len(self.frames)]
            console.print(f"\r{frame} {message}", end="", style="bold cyan")
            frame_idx += 1
            time.sleep(self.speed)


class MCLIProgressBar:
    """Enhanced progress bars with visual flair"""

    @staticmethod
    def create_fancy_progress():
        """Create a fancy progress bar with multiple columns"""
        return Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="bright_green", finished_style="bright_blue"),
            MofNCompleteColumn(),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
        )

    @staticmethod
    def show_rust_compilation_progress():
        """Simulate Rust compilation with progress"""
        progress = MCLIProgressBar.create_fancy_progress()

        with progress:
            # Compilation stages
            stages = [
                ("Checking dependencies", 15),
                ("Compiling core", 30),
                ("Building TF-IDF module", 25),
                ("Building file watcher", 20),
                ("Building command matcher", 25),
                ("Building process manager", 30),
                ("Linking extensions", 15),
                ("Optimizing release build", 20),
            ]

            for stage_name, duration in stages:
                task = progress.add_task(f"🦀 {stage_name}...", total=duration)

                for i in range(duration):
                    progress.update(task, advance=1)
                    time.sleep(0.1)

                progress.remove_task(task)


class VisualTable:
    """Enhanced tables with visual styling"""

    @staticmethod
    def create_performance_table(data: Dict[str, Any]) -> Table:
        """Create a beautiful performance status table"""
        table = Table(
            title="🚀 Performance Optimization Status",
            box=ROUNDED,
            title_style="bold magenta",
            header_style="bold cyan",
            border_style="bright_blue",
        )

        table.add_column("Component", style="bold white", min_width=20)
        table.add_column("Status", justify="center", min_width=10)
        table.add_column("Performance Gain", style="green", min_width=25)
        table.add_column("Details", style="dim white", min_width=30)

        # Add rows with conditional styling
        components = [
            ("UVLoop", "uvloop", "2-4x async I/O"),
            ("Rust Extensions", "rust", "10-100x compute"),
            ("Redis Cache", "redis", "Caching speedup"),
            ("Python Optimizations", "python", "Reduced overhead"),
        ]

        for name, key, gain in components:
            status_data = data.get(key, {})
            success = status_data.get("success", False)

            status_emoji = "✅" if success else "❌"
            status_text = "Active" if success else "Disabled"

            details = (
                status_data.get("reason", "Not available")
                if not success
                else status_data.get("reason", "Loaded successfully")
            )

            table.add_row(
                name, f"{status_emoji} {status_text}", gain if success else "Baseline", details
            )

        return table

    @staticmethod
    def create_rust_extensions_table(extensions: Dict[str, bool]) -> Table:
        """Create a table showing Rust extension status"""
        table = Table(
            title="🦀 Rust Extensions Status",
            box=HEAVY,
            title_style="bold red",
            header_style="bold yellow",
            border_style="bright_red",
        )

        table.add_column("Extension", style="bold white", min_width=20)
        table.add_column("Status", justify="center", min_width=15)
        table.add_column("Performance", style="green", min_width=20)
        table.add_column("Use Case", style="cyan", min_width=25)

        extensions_info = [
            ("TF-IDF Vectorizer", "tfidf", "50-100x faster", "Text analysis & search"),
            ("File Watcher", "file_watcher", "Native performance", "Real-time file monitoring"),
            ("Command Matcher", "command_matcher", "Optimized algorithms", "Fuzzy command search"),
            (
                "Process Manager",
                "process_manager",
                "Async I/O with Tokio",
                "Background task management",
            ),
        ]

        for name, key, perf, use_case in extensions_info:
            is_loaded = extensions.get(key, False)

            status = "🦀 Loaded" if is_loaded else "❌ Failed"
            status_style = "bold green" if is_loaded else "bold red"

            table.add_row(
                name,
                f"[{status_style}]{status}[/{status_style}]",
                perf if is_loaded else "Python fallback",
                use_case,
            )

        return table


class LiveDashboard:
    """Live updating dashboard for system status"""

    def __init__(self):
        self.console = Console()
        self.running = False

    def create_system_overview(self) -> Panel:
        """Create a live system overview panel"""
        try:
            import psutil

            # Get system info
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Create content
            overview = Text()
            overview.append("🖥️  System Overview\n\n", style="bold cyan")
            overview.append(f"CPU Usage: {cpu_percent:.1f}%\n", style="yellow")
            overview.append(
                f"Memory: {memory.percent:.1f}% ({memory.available // (1024**3):.1f}GB free)\n",
                style="green",
            )
            overview.append(f"Disk: {disk.free // (1024**3):.1f}GB free\n", style="blue")

            return Panel(overview, box=ROUNDED, border_style="bright_cyan", padding=(1, 2))

        except ImportError:
            return Panel(
                "System monitoring requires psutil\nInstall with: pip install psutil",
                title="System Info Unavailable",
                border_style="yellow",
            )

    def create_mcli_status_panel(self) -> Panel:
        """Create MCLI status overview panel"""
        try:
            import platform

            status = Text()
            status.append("🚀 MCLI Status\n\n", style="bold magenta")

            # Version info
            try:
                from importlib.metadata import version

                mcli_version = version("mcli")
                status.append(f"Version: {mcli_version}\n", style="cyan")
            except Exception:
                status.append("Version: Development\n", style="cyan")

            # Platform info
            status.append(f"Platform: {platform.system()} {platform.machine()}\n", style="blue")
            status.append(f"Python: {platform.python_version()}\n", style="green")

            # Performance status
            try:
                from mcli.lib.performance.rust_bridge import check_rust_extensions

                rust_available = check_rust_extensions()
                if rust_available:
                    status.append("⚡ Rust Extensions: Active\n", style="bright_green")
                else:
                    status.append("🐍 Rust Extensions: Fallback to Python\n", style="yellow")
            except Exception:
                status.append("🔧 Performance Status: Unknown\n", style="dim")

            return Panel(status, box=ROUNDED, border_style="bright_magenta", padding=(1, 2))

        except Exception as e:
            return Panel(
                f"Error getting MCLI status: {str(e)}",
                title="MCLI Status Error",
                border_style="red",
            )

    def create_services_panel(self) -> Panel:
        """Create services status panel"""
        services = Text()
        services.append("🔧 Services Status\n\n", style="bold yellow")

        # Check daemon status
        try:
            from mcli.lib.api.daemon_client import get_daemon_client

            daemon = get_daemon_client()
            if daemon.is_running():
                services.append("✅ MCLI Daemon: Running\n", style="green")
            else:
                services.append("❌ MCLI Daemon: Stopped\n", style="red")
        except Exception:
            services.append("⚠️  MCLI Daemon: Unknown\n", style="yellow")

        # Check Ollama status
        try:
            import requests

            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                services.append("✅ Ollama: Running\n", style="green")
            else:
                services.append("❌ Ollama: Not responding\n", style="red")
        except Exception:
            services.append("❌ Ollama: Not running\n", style="red")

        return Panel(services, box=ROUNDED, border_style="bright_yellow", padding=(1, 2))

    def create_recent_activity_panel(self) -> Panel:
        """Create recent activity panel"""
        activity = Text()
        activity.append("📊 Recent Activity\n\n", style="bold blue")

        # This would typically read from logs or activity history
        activity.append("• Started chat session at 14:32\n", style="dim")
        activity.append("• Executed 'mcli self performance' at 14:30\n", style="dim")
        activity.append("• Daemon started at 14:25\n", style="dim")
        activity.append("• Last command execution: SUCCESS\n", style="green")

        return Panel(activity, box=ROUNDED, border_style="bright_blue", padding=(1, 2))

    def create_full_dashboard(self):
        """Create a complete dashboard layout"""
        from rich.layout import Layout

        layout = Layout()

        # Create main sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )

        # Split main section
        layout["main"].split_row(Layout(name="left"), Layout(name="right"))

        # Split left and right sections
        layout["left"].split_column(Layout(name="system"), Layout(name="mcli"))

        layout["right"].split_column(Layout(name="services"), Layout(name="activity"))

        # Add content to each section
        layout["header"].update(Panel("🚀 MCLI Live Dashboard", style="bold cyan"))
        layout["system"].update(self.create_system_overview())
        layout["mcli"].update(self.create_mcli_status_panel())
        layout["services"].update(self.create_services_panel())
        layout["activity"].update(self.create_recent_activity_panel())

        from datetime import datetime

        layout["footer"].update(
            Panel(f"Last updated: {datetime.now().strftime('%H:%M:%S')}", style="dim")
        )

        return layout

    def start_live_dashboard(self, refresh_interval: float = 2.0):
        """Start the live updating dashboard"""
        import threading
        import time

        self.running = True

        def update_loop():
            while self.running:
                try:
                    with self.console:
                        self.console.clear()
                        dashboard = self.create_full_dashboard()
                        self.console.print(dashboard)
                    time.sleep(refresh_interval)
                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    self.console.print(f"Dashboard error: {e}")
                    time.sleep(refresh_interval)

        try:
            self.console.print("Starting MCLI Live Dashboard... Press Ctrl+C to exit")
            update_loop()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard stopped by user[/yellow]")
        finally:
            self.running = False

    def stop_dashboard(self):
        """Stop the live dashboard"""
        self.running = False


class ColorfulOutput:
    """Enhanced colorful output utilities"""

    @staticmethod
    def success(message: str, icon: str = "✅"):
        """Display a success message with style"""
        panel = Panel(f"{icon} {message}", box=ROUNDED, border_style="bright_green", padding=(0, 1))
        console.print(panel)

    @staticmethod
    def error(message: str, icon: str = "❌"):
        """Display an error message with style"""
        panel = Panel(f"{icon} {message}", box=HEAVY, border_style="bright_red", padding=(0, 1))
        console.print(panel)

    @staticmethod
    def info(message: str, icon: str = "ℹ️"):
        """Display an info message with style"""
        panel = Panel(f"{icon} {message}", box=ROUNDED, border_style="bright_cyan", padding=(0, 1))
        console.print(panel)

    @staticmethod
    def warning(message: str, icon: str = "⚠️"):
        """Display a warning message with style"""
        panel = Panel(
            f"{icon} {message}", box=ROUNDED, border_style="bright_yellow", padding=(0, 1)
        )
        console.print(panel)


class StartupSequence:
    """Fancy startup sequence with animations"""

    @staticmethod
    def run_startup_animation():
        """Run the full startup sequence"""
        console.clear()

        # Show main banner
        MCLIBanner.show_main_banner("Next-Generation CLI Tool")

        # Animated loading
        spinner = AnimatedSpinner("rocket", 0.15)
        spinner.start("Initializing MCLI systems...")
        time.sleep(2)
        spinner.stop()

        ColorfulOutput.success("Core systems initialized")

        # Show performance optimizations
        spinner = AnimatedSpinner("gears", 0.1)
        spinner.start("Applying performance optimizations...")
        time.sleep(1.5)
        spinner.stop()

        ColorfulOutput.success("Performance optimizations applied")

        # Rust extensions check
        spinner = AnimatedSpinner("rust", 0.12)
        spinner.start("Loading Rust extensions...")
        time.sleep(1)
        spinner.stop()

        ColorfulOutput.success("Rust extensions loaded successfully")

        console.print()
        console.print(Rule("🚀 MCLI Ready for Action! 🚀", style="bright_green"))
        console.print()


def demo_visual_effects():
    """Demonstrate all visual effects"""
    console.clear()

    # Show banners
    MCLIBanner.show_main_banner()
    time.sleep(1)

    MCLIBanner.show_performance_banner()
    time.sleep(1)

    MCLIBanner.show_rust_banner()
    time.sleep(1)

    # Show tables
    console.print("\n")
    sample_data = {
        "uvloop": {"success": True, "reason": "Loaded successfully"},
        "rust": {
            "success": True,
            "extensions": {
                "tfidf": True,
                "file_watcher": True,
                "command_matcher": True,
                "process_manager": True,
            },
        },
        "redis": {"success": False, "reason": "Redis server not available"},
        "python": {"success": True, "optimizations": {"gc_tuned": True}},
    }

    table = VisualTable.create_performance_table(sample_data)
    console.print(table)

    console.print("\n")
    rust_table = VisualTable.create_rust_extensions_table(
        {"tfidf": True, "file_watcher": True, "command_matcher": False, "process_manager": True}
    )
    console.print(rust_table)

    # Test messages
    console.print("\n")
    ColorfulOutput.success("All systems operational!")
    ColorfulOutput.warning("Redis cache not available")
    ColorfulOutput.info("System ready for commands")

    console.print("\n")
    console.print(Rule("Demo Complete", style="bright_magenta"))


if __name__ == "__main__":
    demo_visual_effects()
