"""
Fuzzy command finding for MCLI.

Provides intelligent command matching using fuzzy string matching algorithms.
"""

from typing import Any, Dict, List, Optional, Tuple

from fuzzywuzzy import fuzz, process

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class FuzzyCommandFinder:
    """Fuzzy finder for MCLI commands."""

    def __init__(self, min_score: int = 60, max_results: int = 10):
        """
        Initialize fuzzy finder.

        Args:
            min_score: Minimum similarity score (0-100)
            max_results: Maximum number of results to return
        """
        self.min_score = min_score
        self.max_results = max_results

    def find_commands(
        self, query: str, commands: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], int]]:
        """
        Find commands using fuzzy matching.

        Args:
            query: Search query
            commands: List of command dictionaries

        Returns:
            List of (command, score) tuples sorted by score (descending)
        """
        if not query:
            # No query - return all commands with score 100
            return [(cmd, 100) for cmd in commands]

        query_lower = query.lower()
        results = []

        for cmd in commands:
            name = cmd.get("full_name", cmd.get("name", ""))
            description = cmd.get("description", "")

            # Calculate various match scores
            scores = []

            # 1. Exact match (highest priority)
            if name.lower() == query_lower:
                scores.append(100)

            # 2. Prefix match
            if name.lower().startswith(query_lower):
                scores.append(95)

            # 3. Fuzzy ratio on name
            name_ratio = fuzz.ratio(query_lower, name.lower())
            scores.append(name_ratio)

            # 4. Partial ratio (substring matching)
            partial_ratio = fuzz.partial_ratio(query_lower, name.lower())
            scores.append(partial_ratio)

            # 5. Token set ratio (handles word order differences)
            token_ratio = fuzz.token_set_ratio(query_lower, name.lower())
            scores.append(token_ratio)

            # 6. Acronym match (e.g., "gst" → "git_status")
            acronym_score = self._match_acronym(query_lower, name.lower())
            if acronym_score > 0:
                scores.append(acronym_score)

            # 7. Match against description (lower weight)
            if description:
                desc_ratio = fuzz.partial_ratio(query_lower, description.lower())
                scores.append(desc_ratio * 0.5)  # 50% weight

            # Take best score
            final_score = int(max(scores))

            if final_score >= self.min_score:
                results.append((cmd, final_score))

        # Sort by score (descending), then by name
        results.sort(key=lambda x: (-x[1], x[0].get("name", "")))

        return results[: self.max_results]

    def get_best_matches(
        self, query: str, commands: List[Dict[str, Any]], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top N best matching commands.

        Args:
            query: Search query
            commands: List of command dictionaries
            limit: Maximum number of results (default: self.max_results)

        Returns:
            List of command dictionaries
        """
        if limit is None:
            limit = self.max_results

        matches = self.find_commands(query, commands)
        return [cmd for cmd, score in matches[:limit]]

    def get_single_best_match(
        self, query: str, commands: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Get single best matching command.

        Args:
            query: Search query
            commands: List of command dictionaries

        Returns:
            Best matching command or None
        """
        matches = self.find_commands(query, commands)
        if matches:
            return matches[0][0]
        return None

    def _match_acronym(self, query: str, name: str) -> int:
        """
        Match query against acronym of name.

        For example:
        - "gst" matches "git_status" → high score
        - "bdb" matches "backup_db" → high score

        Args:
            query: Search query
            name: Command name

        Returns:
            Acronym match score (0-100)
        """
        # Extract acronym from name (first letter of each word)
        parts = name.replace("-", "_").split("_")
        acronym = "".join(part[0] for part in parts if part)

        if not acronym:
            return 0

        # Check if query matches acronym
        if query == acronym:
            return 85  # High score for exact acronym match

        # Partial acronym match
        if acronym.startswith(query):
            return 75

        # Fuzzy acronym match
        if len(query) >= 2:
            ratio = fuzz.ratio(query, acronym)
            if ratio > 70:
                return ratio

        return 0

    def get_match_explanation(self, query: str, command: Dict[str, Any]) -> str:
        """
        Get explanation of why a command matched.

        Args:
            query: Search query
            command: Command dictionary

        Returns:
            Human-readable explanation
        """
        name = command.get("full_name", command.get("name", ""))
        query_lower = query.lower()
        name_lower = name.lower()

        if name_lower == query_lower:
            return "exact match"
        elif name_lower.startswith(query_lower):
            return "prefix match"
        elif query_lower in name_lower:
            return "substring match"
        else:
            # Check acronym
            parts = name.replace("-", "_").split("_")
            acronym = "".join(part[0] for part in parts if part)
            if acronym and query_lower == acronym:
                return f"acronym match ({acronym})"
            elif acronym and acronym.startswith(query_lower):
                return f"partial acronym ({acronym})"
            else:
                return "fuzzy match"


def create_fuzzy_finder(min_score: int = 60, max_results: int = 10) -> FuzzyCommandFinder:
    """
    Create a fuzzy command finder instance.

    Args:
        min_score: Minimum similarity score (0-100)
        max_results: Maximum number of results

    Returns:
        FuzzyCommandFinder instance
    """
    return FuzzyCommandFinder(min_score=min_score, max_results=max_results)
