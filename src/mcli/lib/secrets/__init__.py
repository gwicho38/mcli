"""
Secrets management module for MCLI.

Provides secure storage and retrieval of secrets with git-based synchronization.
"""

from .manager import SecretsManager
from .store import SecretsStore

__all__ = ["SecretsManager", "SecretsStore"]
