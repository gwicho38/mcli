"""
Interactive command selector for MCLI.

Provides an interactive fuzzy-finding interface for command selection.
"""

import sys
from typing import Any, Dict, List, Optional

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from mcli.lib.fuzzy_finder import FuzzyCommandFinder
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


def format_command_display(cmd: Dict[str, Any], show_score: bool = False, score: int = 0) -> str:
    """
    Format command for display in selector.

    Args:
        cmd: Command dictionary
        show_score: Whether to show match score
        score: Match score (0-100)

    Returns:
        Formatted display string
    """
    name = cmd.get("full_name", cmd.get("name", ""))
    description = cmd.get("description", "")
    language = cmd.get("language", "python")

    # Build display string
    parts = [name]

    # Add language badge
    if language == "shell":
        parts.append(f"({language})")

    # Add score if requested
    if show_score and score > 0:
        parts.append(f"[{score}%]")

    # Add description
    if description:
        # Truncate long descriptions
        max_desc_len = 60
        if len(description) > max_desc_len:
            description = description[:max_desc_len] + "..."
        parts.append(f"- {description}")

    return " ".join(parts)


def select_command_interactive(
    commands: List[Dict[str, Any]],
    query: str = "",
    show_scores: bool = False,
    fuzzy_finder: Optional[FuzzyCommandFinder] = None,
) -> Optional[Dict[str, Any]]:
    """
    Interactive command selection with fuzzy finding.

    Args:
        commands: List of available commands
        query: Initial search query
        show_scores: Whether to show match scores
        fuzzy_finder: FuzzyCommandFinder instance (creates default if None)

    Returns:
        Selected command dictionary or None if cancelled
    """
    if not commands:
        logger.warning("No commands available for selection")
        return None

    # Check if running in interactive terminal
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        logger.error("Interactive selector requires a TTY")
        # Fall back to first match in non-interactive mode
        if query and fuzzy_finder:
            best_match = fuzzy_finder.get_single_best_match(query, commands)
            if best_match:
                return best_match
        return None

    # Create fuzzy finder if not provided
    if fuzzy_finder is None:
        fuzzy_finder = FuzzyCommandFinder()

    # Get matches with scores
    if query:
        matches = fuzzy_finder.find_commands(query, commands)
        message = f"Select a command matching '{query}':"
    else:
        matches = [(cmd, 100) for cmd in commands]
        message = "Select a workflow command:"

    if not matches:
        logger.warning(f"No commands found matching '{query}'")
        return None

    # Create choices for inquirer
    choices = []
    for cmd, score in matches:
        display = format_command_display(cmd, show_scores, score)
        choices.append(Choice(value=cmd, name=display))

    try:
        # Use fuzzy select for interactive searching
        selected = inquirer.fuzzy(
            message=message,
            choices=choices,
            default=choices[0].value if choices else None,
            max_height="70%",
            instruction="(Type to search, ↑↓ to navigate, Enter to select, Ctrl+C to cancel)",
        ).execute()

        return selected

    except (KeyboardInterrupt, EOFError):
        logger.info("Command selection cancelled by user")
        return None
    except Exception as e:
        logger.error(f"Error during command selection: {e}")
        return None


def select_from_suggestions(
    query: str, commands: List[Dict[str, Any]], fuzzy_finder: Optional[FuzzyCommandFinder] = None
) -> Optional[Dict[str, Any]]:
    """
    Show "Did you mean?" suggestions for unknown commands.

    Args:
        query: The unknown command that was attempted
        commands: List of available commands
        fuzzy_finder: FuzzyCommandFinder instance

    Returns:
        Selected command or None
    """
    if fuzzy_finder is None:
        fuzzy_finder = FuzzyCommandFinder(min_score=50)  # Lower threshold for suggestions

    matches = fuzzy_finder.find_commands(query, commands)

    if not matches:
        return None

    # Check if running in interactive terminal
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        # Non-interactive: return best match if score is high enough
        if matches[0][1] >= 80:  # High confidence match
            return matches[0][0]
        return None

    # Show top 5 suggestions
    top_matches = matches[:5]

    print(f"\n❌ Command '{query}' not found.")
    print(f"\n💡 Did you mean one of these?\n")

    choices = []
    for i, (cmd, score) in enumerate(top_matches, 1):
        name = cmd.get("full_name", cmd.get("name", ""))
        description = cmd.get("description", "")
        display = f"{name}"
        if description:
            display += f" - {description[:50]}"
        choices.append(Choice(value=cmd, name=display))

    # Add "None of these" option
    choices.append(Choice(value=None, name="❌ None of these"))

    try:
        selected = inquirer.select(
            message="Select a command:",
            choices=choices,
            default=choices[0].value,
        ).execute()

        return selected

    except (KeyboardInterrupt, EOFError):
        logger.info("Suggestion selection cancelled")
        return None


def quick_select_best_match(
    query: str, commands: List[Dict[str, Any]], min_score: int = 90
) -> Optional[Dict[str, Any]]:
    """
    Quickly select best match without interaction if score is high enough.

    Args:
        query: Search query
        commands: Available commands
        min_score: Minimum score for auto-selection

    Returns:
        Best matching command if score >= min_score, else None
    """
    finder = FuzzyCommandFinder()
    matches = finder.find_commands(query, commands)

    if matches and matches[0][1] >= min_score:
        return matches[0][0]

    return None
