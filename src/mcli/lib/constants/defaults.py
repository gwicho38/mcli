"""Default value constants for mcli.

This module defines all default values used throughout the mcli application.
Using these constants ensures consistency and makes configuration easier.
"""

from typing import List


class Editors:
    """Editor-related constants."""

    DEFAULT = "vim"
    FALLBACK_LIST: List[str] = ["vim", "nano", "code", "subl", "atom", "emacs"]


class Shells:
    """Shell-related constants."""

    DEFAULT = "bash"
    DEFAULT_PATH = "/bin/bash"
    SUPPORTED: List[str] = ["bash", "zsh", "fish", "sh"]


class URLs:
    """URL constants for various services."""

    # Local development
    LSH_API_DEFAULT = "http://localhost:3030"
    OLLAMA_DEFAULT = "http://localhost:8080"
    LOCALHOST = "http://localhost"

    # Trading/Finance APIs
    ALPACA_PAPER = "https://paper-api.alpaca.markets"
    ALPACA_DATA = "https://data.alpaca.markets"
    ALPACA_LIVE = "https://api.alpaca.markets"

    # GitHub APIs
    GITHUB_API = "https://api.github.com"
    GITHUB_API_MCLI = "https://api.github.com/repos/gwicho38/mcli"
    GITHUB_API_ACTIONS = "https://api.github.com/repos/gwicho38/mcli/actions/runs"

    # PyPI
    PYPI_API = "https://pypi.org/pypi"
    PYPI_MCLI = "https://pypi.org/pypi/mcli-framework/json"

    # MLFlow
    MLFLOW_DEFAULT = "http://localhost:5000"


class Languages:
    """Programming language constants."""

    PYTHON = "python"
    SHELL = "shell"
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


class LogLevels:
    """Logging level constants."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    NOTSET = "NOTSET"


class HTTPMethods:
    """HTTP method constants."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class Timeouts:
    """Timeout constants (in seconds)."""

    DEFAULT_HTTP = 30
    LONG_RUNNING = 300
    SHORT = 10
    VERY_SHORT = 5


class DateFormats:
    """Date and time format constants."""

    ISO_8601 = "%Y-%m-%dT%H:%M:%S"
    ISO_8601_WITH_Z = "%Y-%m-%dT%H:%M:%SZ"
    ISO_8601_MS = "%Y-%m-%dT%H:%M:%S.%f"
    DATE_ONLY = "%Y-%m-%d"
    TIME_ONLY = "%H:%M:%S"
    HUMAN_READABLE = "%Y-%m-%d %H:%M:%S"


class Encoding:
    """Text encoding constants."""

    UTF8 = "utf-8"
    ASCII = "ascii"
    LATIN1 = "latin-1"


__all__ = [
    "Editors",
    "Shells",
    "URLs",
    "Languages",
    "LogLevels",
    "HTTPMethods",
    "Timeouts",
    "DateFormats",
    "Encoding",
]
