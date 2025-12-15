"""Script and workflow constants for mcli.

This module defines constants related to script languages, file extensions,
metadata, and workflow configuration used throughout the mcli application.
"""

from typing import Dict, List


class ScriptLanguages:
    """Supported script language identifiers.

    These are the canonical language names used internally by mcli.
    Use these constants instead of raw strings for type safety and consistency.

    Example:
        if language == ScriptLanguages.PYTHON:
            # handle Python script
    """

    PYTHON = "python"
    SHELL = "shell"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    IPYNB = "ipynb"

    # All supported languages as a list (useful for validation)
    ALL: List[str] = [PYTHON, SHELL, JAVASCRIPT, TYPESCRIPT, IPYNB]


class ScriptExtensions:
    """File extensions for script languages.

    Maps language identifiers to their canonical file extensions.

    Example:
        ext = ScriptExtensions.BY_LANGUAGE[ScriptLanguages.PYTHON]  # ".py"
    """

    # Primary extensions
    PYTHON = ".py"
    SHELL = ".sh"
    SHELL_BASH = ".bash"
    JAVASCRIPT = ".js"
    TYPESCRIPT = ".ts"
    IPYNB = ".ipynb"

    # Language to extension mapping (canonical extension for each language)
    BY_LANGUAGE: Dict[str, str] = {
        ScriptLanguages.PYTHON: PYTHON,
        ScriptLanguages.SHELL: SHELL,
        ScriptLanguages.JAVASCRIPT: JAVASCRIPT,
        ScriptLanguages.TYPESCRIPT: TYPESCRIPT,
        ScriptLanguages.IPYNB: IPYNB,
    }

    # Extension to language mapping (for detection)
    TO_LANGUAGE: Dict[str, str] = {
        PYTHON: ScriptLanguages.PYTHON,
        SHELL: ScriptLanguages.SHELL,
        SHELL_BASH: ScriptLanguages.SHELL,
        JAVASCRIPT: ScriptLanguages.JAVASCRIPT,
        TYPESCRIPT: ScriptLanguages.TYPESCRIPT,
        IPYNB: ScriptLanguages.IPYNB,
    }

    # All supported extensions
    ALL: List[str] = [PYTHON, SHELL, SHELL_BASH, JAVASCRIPT, TYPESCRIPT, IPYNB]


class ScriptCommentPrefixes:
    """Comment prefixes by script language.

    Used for adding/parsing metadata comments in scripts.

    Example:
        prefix = ScriptCommentPrefixes.BY_LANGUAGE[ScriptLanguages.PYTHON]  # "#"
    """

    HASH = "#"
    DOUBLE_SLASH = "//"

    BY_LANGUAGE: Dict[str, str] = {
        ScriptLanguages.PYTHON: HASH,
        ScriptLanguages.SHELL: HASH,
        ScriptLanguages.JAVASCRIPT: DOUBLE_SLASH,
        ScriptLanguages.TYPESCRIPT: DOUBLE_SLASH,
        # Note: ipynb uses JSON metadata, not comments
    }


class ScriptMetadataKeys:
    """Metadata keys used in script comments.

    These keys are used with @-prefixed comments in scripts:
        # @description: My script description
        # @version: 1.0.0

    Example:
        pattern = f"@{ScriptMetadataKeys.DESCRIPTION}:"
    """

    DESCRIPTION = "description"
    VERSION = "version"
    AUTHOR = "author"
    GROUP = "group"
    REQUIRES = "requires"
    TAGS = "tags"
    SHELL = "shell"

    # Keys that contain comma-separated lists
    LIST_KEYS: List[str] = [REQUIRES, TAGS]


class ScriptMetadataDefaults:
    """Default values for script metadata.

    Example:
        metadata = {
            ScriptMetadataKeys.VERSION: ScriptMetadataDefaults.VERSION,
            ScriptMetadataKeys.GROUP: ScriptMetadataDefaults.GROUP,
        }
    """

    DESCRIPTION = ""
    VERSION = "1.0.0"
    AUTHOR = ""
    GROUP = "workflows"
    SHELL = "bash"


class ShellTypes:
    """Supported shell types for shell scripts.

    Example:
        if shell_type in ShellTypes.ALL:
            # valid shell type
    """

    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    SH = "sh"

    ALL: List[str] = [BASH, ZSH, FISH, SH]
    DEFAULT = BASH


__all__ = [
    "ScriptLanguages",
    "ScriptExtensions",
    "ScriptCommentPrefixes",
    "ScriptMetadataKeys",
    "ScriptMetadataDefaults",
    "ShellTypes",
]
