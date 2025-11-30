"""Environment variable name constants for mcli.

This module defines all environment variable names used throughout the mcli application.
Using these constants ensures consistency and makes it easier to track environment variable usage.
"""


class EnvVars:
    """Environment variable names used in mcli."""

    # MCLI-specific configuration
    MCLI_TRACE_LEVEL = "MCLI_TRACE_LEVEL"
    MCLI_CONFIG = "MCLI_CONFIG"
    MCLI_HOME = "MCLI_HOME"
    MCLI_DEBUG = "MCLI_DEBUG"
    MCLI_ENV = "MCLI_ENV"
    MCLI_AUTO_OPTIMIZE = "MCLI_AUTO_OPTIMIZE"
    MCLI_PLUGIN_PATH = "MCLI_PLUGIN_PATH"
    MCLI_INCLUDE_TEST_COMMANDS = "MCLI_INCLUDE_TEST_COMMANDS"
    MCLI_COMMAND = "MCLI_COMMAND"
    MCLI_SHOW_PERFORMANCE_SUMMARY = "MCLI_SHOW_PERFORMANCE_SUMMARY"
    MCLI_NOTEBOOK_EXECUTE = "MCLI_NOTEBOOK_EXECUTE"

    # API Keys - OpenAI
    OPENAI_API_KEY = "OPENAI_API_KEY"
    OPENAI_ORG_ID = "OPENAI_ORG_ID"

    # API Keys - Anthropic
    ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"

    # API Keys - Trading/Finance
    ALPACA_API_KEY = "ALPACA_API_KEY"
    ALPACA_SECRET_KEY = "ALPACA_SECRET_KEY"
    ALPACA_BASE_URL = "ALPACA_BASE_URL"

    # API Keys - LSH (Local Service Handler)
    LSH_API_KEY = "LSH_API_KEY"
    LSH_API_URL = "LSH_API_URL"

    # API Keys - Supabase
    SUPABASE_URL = "SUPABASE_URL"
    SUPABASE_KEY = "SUPABASE_KEY"
    SUPABASE_ANON_KEY = "SUPABASE_ANON_KEY"
    SUPABASE_SERVICE_ROLE_KEY = "SUPABASE_SERVICE_ROLE_KEY"

    # System environment variables
    SHELL = "SHELL"
    EDITOR = "EDITOR"
    XDG_DATA_HOME = "XDG_DATA_HOME"
    PYTHONOPTIMIZE = "PYTHONOPTIMIZE"
    HOME = "HOME"
    PATH = "PATH"

    # Database
    DATABASE_URL = "DATABASE_URL"
    ASYNC_DATABASE_URL = "ASYNC_DATABASE_URL"

    # Shell completion
    COMPLETE = "_MCLI_COMPLETE"

    # CI/CD
    CI = "CI"
    GITHUB_ACTIONS = "GITHUB_ACTIONS"
    GITHUB_TOKEN = "GITHUB_TOKEN"


__all__ = ["EnvVars"]
