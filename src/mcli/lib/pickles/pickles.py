import io
import os
import pickle
from pathlib import Path
from typing import Callable, Generic, Type, TypeVar

T = TypeVar("T")


class RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that only allows deserializing a specific class."""

    def __init__(self, file: io.BufferedIOBase, allowed_class: Type):
        super().__init__(file)
        self.allowed_class = allowed_class

    def find_class(self, module: str, name: str) -> Type:
        if name == self.allowed_class.__name__:
            return self.allowed_class
        raise pickle.UnpicklingError(f"Forbidden class: {module}.{name}")


# Allowlist of (module, qualified-name) globals that are safe to reconstruct
# from untrusted pickle data: builtin containers/scalars plus numpy array
# primitives. Anything else (callables like os.system/eval, arbitrary classes)
# is rejected, closing the pickle-RCE vector when deserializing cache data.
_SAFE_GLOBALS = {
    ("builtins", "list"),
    ("builtins", "dict"),
    ("builtins", "tuple"),
    ("builtins", "set"),
    ("builtins", "frozenset"),
    ("builtins", "str"),
    ("builtins", "bytes"),
    ("builtins", "bytearray"),
    ("builtins", "int"),
    ("builtins", "float"),
    ("builtins", "complex"),
    ("builtins", "bool"),
    ("builtins", "NoneType"),
    # numpy array reconstruction primitives (only used when numpy is installed)
    ("numpy", "ndarray"),
    ("numpy", "dtype"),
    ("numpy.core.multiarray", "_reconstruct"),
    ("numpy.core.multiarray", "scalar"),
    ("numpy._core.multiarray", "_reconstruct"),
    ("numpy._core.multiarray", "scalar"),
}


class SafeUnpickler(pickle.Unpickler):
    """Unpickler restricted to an allowlist of safe builtin/numpy globals.

    Use for deserializing data from untrusted or shared stores (e.g. a Redis
    cache) where a poisoned entry could otherwise trigger arbitrary code
    execution via pickle reduce gadgets.
    """

    def find_class(self, module: str, name: str) -> Type:
        if (module, name) in _SAFE_GLOBALS:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"Forbidden global during unpickling: {module}.{name}")


def safe_loads(data: bytes):
    """Deserialize *data* allowing only safe builtin/numpy globals.

    Raises ``pickle.UnpicklingError`` for anything outside the allowlist.
    """
    return SafeUnpickler(io.BytesIO(data)).load()


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
                    obj = RestrictedUnpickler(f, self.class_type).load()
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
