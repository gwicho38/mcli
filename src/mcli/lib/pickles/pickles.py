import os
import pickle
from pathlib import Path
from typing import Callable, Generic, Type, TypeVar

import click

T = TypeVar("T")


class ObjectCache(Generic[T]):
    def __init__(self, class_type: Type[T], app_name: str, factory: Callable[[], T] = None):
        self.class_type = class_type
        self.app_name = app_name
        self.factory = factory or class_type

    def get_cache_path(self) -> Path:
        cache_dir = Path(os.path.expanduser(f"~/.cache/{self.app_name}"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{self.class_type.__name__.lower()}.pickle"

    def get_or_create(self) -> T:
        cache_path = self.get_cache_path()

        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    obj = pickle.load(f)
                    if isinstance(obj, self.class_type):
                        return obj
            except (pickle.UnpicklingError, EOFError):
                cache_path.unlink()

        # Create new instance if no cache exists or loading failed
        obj = self.factory()

        # Save to cache
        with open(cache_path, "wb") as f:
            pickle.dump(obj, f)

        return obj

    def clear(self) -> None:
        """Remove the cached object if it exists."""
        cache_path = self.get_cache_path()
        if cache_path.exists():
            cache_path.unlink()


__all__ = ["ObjectCache"]
