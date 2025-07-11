from rich.console import Console

console = Console()


def info(message: str) -> None:
    """Display an informational message with cyan coloring.
    
    Args:
        message: The text to display
    """
    console.print(f"[bold cyan]ℹ️  {message}[/bold cyan]")

def warning(message: str) -> None:
    """Display a warning message in yellow."""
    console.print(f"[bold yellow]⚠️  {message}[/bold yellow]")


def success(message: str) -> None:
    """Display a success message in green."""
    console.print(f"[bold green]{message}[/bold green]")


def error(message: str) -> None:
    """Display an error message in red."""
    console.print(f"[bold red]{message}[/bold red]")
