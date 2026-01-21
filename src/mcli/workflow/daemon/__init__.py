"""
Daemon service for command management and execution.

This module provides a background daemon service that can store, manage, and execute
commands written in various programming languages (Python, Node.js, Lua, Shell).
Commands are stored in a SQLite database with embeddings for similarity search and
hierarchical grouping.

The daemon CLI commands are now loaded from portable JSON files in ~/.mcli/commands/
"""

from .daemon import Command, CommandExecutor, DaemonService

# Export main components
__all__ = ["Command", "CommandExecutor", "DaemonService"]
