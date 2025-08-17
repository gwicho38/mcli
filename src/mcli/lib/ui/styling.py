from rich.box import HEAVY, ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def info(message: str) -> None:
    """Display an informational message with enhanced styling.

    Args:
        message: The text to display
    """
    panel = Panel(f"ℹ️  {message}", box=ROUNDED, border_style="bright_cyan", padding=(0, 1))
    console.print(panel)


def warning(message: str) -> None:
    """Display a warning message with enhanced styling."""
    panel = Panel(f"⚠️  {message}", box=ROUNDED, border_style="bright_yellow", padding=(0, 1))
    console.print(panel)


def success(message: str) -> None:
    """Display a success message with enhanced styling."""
    panel = Panel(f"✅ {message}", box=ROUNDED, border_style="bright_green", padding=(0, 1))
    console.print(panel)


def error(message: str) -> None:
    """Display an error message with enhanced styling."""
    panel = Panel(f"❌ {message}", box=HEAVY, border_style="bright_red", padding=(0, 1))
    console.print(panel)


def celebrate(message: str) -> None:
    """Display a celebration message with extra flair."""
    panel = Panel(
        f"🎉 {message} 🎉",
        title="🌟 SUCCESS 🌟",
        title_align="center",
        box=HEAVY,
        border_style="bright_magenta",
        padding=(1, 2),
    )
    console.print(panel)
