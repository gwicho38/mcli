from rich.console import Console

console = Console()


def info(message: str) -> None:
    """Display an informational message with cyan coloring."""
    console.print(f"[bold cyan]{message}[/bold cyan]")


def success(message: str) -> None:
    """Display a success message in green."""
    console.print(f"[bold green]{message}[/bold green]")


def error(message: str) -> None:
    """Display an error message in red."""
    console.print(f"[bold red]{message}[/bold red]")
