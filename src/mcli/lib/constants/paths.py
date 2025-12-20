"""File and directory path constants for mcli.

This module defines all file and directory names used throughout the mcli application.
Using these constants ensures consistency across the codebase.
"""


class DirNames:
    """Directory name constants."""

    MCLI = ".mcli"
    GIT = ".git"
    LOGS = "logs"
    CONFIG = "config"
    DATA = "data"
    CACHE = "cache"
    PLUGINS = "plugins"
    COMMANDS = "commands"
    WORKFLOWS = "workflows"
    LOCAL = ".local"
    CONFIG_DIR = ".config"
    REPOS = "repos"
    MCLI_COMMANDS = "mcli-commands"
    VENV = "venv"
    DOT_VENV = ".venv"
    DOT_ENV = ".env"
    ENV = "env"
    PYCACHE = "__pycache__"
    RESOURCES = "resources"
    MODELS = "models"
    SCRIPTS = "scripts"
    PRIVATE = "private"
    APP = "app"
    SELF = "self"
    WORKFLOW = "workflow"
    PUBLIC = "public"
    SRC = "src"
    LIB = "Lib"
    SITE_PACKAGES = "site-packages"


class FileNames:
    """File name constants."""

    CONFIG_TOML = "config.toml"
    GITIGNORE = ".gitignore"
    STORE_CONF = "store.conf"
    COMMANDS_LOCK_JSON = "commands.lock.json"
    LSH_ENV = "lsh.env"
    README_MD = "README.md"
    ENV = ".env"
    ENV_EXAMPLE = ".env.example"
    SETUP_PY = "setup.py"
    SETUP_CFG = "setup.cfg"
    INIT_PY = "__init__.py"
    DS_STORE = ".DS_Store"
    PYPROJECT_TOML = "pyproject.toml"
    REQUIREMENTS_TXT = "requirements.txt"
    IPFS_SYNC_HISTORY_JSON = "ipfs_sync_history.json"
    COMMANDS_JSON = "commands.json"


class PathPatterns:
    """File path patterns for matching."""

    BACKUP = "*.backup"
    TEST_PREFIX = ("test_", "test-")
    GITIGNORE_DEFAULT_CONTENT = "*.backup\n.DS_Store\n"


class GitIgnorePatterns:
    """Common .gitignore patterns."""

    BACKUP = "*.backup"
    DS_STORE = ".DS_Store"
    PYCACHE = "__pycache__/"
    PYPROJECT_LOCAL = "*.pyc"
    VENV = "venv/"
    DOT_VENV = ".venv/"
    ENV_LOCAL = ".env.local"
    DIST = "dist/"
    BUILD = "build/"
    EGG_INFO = "*.egg-info/"


__all__ = ["DirNames", "FileNames", "PathPatterns", "GitIgnorePatterns"]
