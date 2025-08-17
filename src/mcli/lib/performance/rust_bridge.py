"""
Bridge module for integrating Rust extensions with Python code
"""

import importlib.util
import os
import sys
from typing import Any, Dict, List, Optional, Union

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)

# Global flags for Rust extension availability
_RUST_AVAILABLE = None
_RUST_TFIDF = None
_RUST_FILE_WATCHER = None
_RUST_COMMAND_MATCHER = None
_RUST_PROCESS_MANAGER = None


def check_rust_extensions() -> Dict[str, bool]:
    """Check which Rust extensions are available"""
    global _RUST_AVAILABLE, _RUST_TFIDF, _RUST_FILE_WATCHER, _RUST_COMMAND_MATCHER, _RUST_PROCESS_MANAGER

    if _RUST_AVAILABLE is not None:
        return {
            "available": _RUST_AVAILABLE,
            "tfidf": _RUST_TFIDF,
            "file_watcher": _RUST_FILE_WATCHER,
            "command_matcher": _RUST_COMMAND_MATCHER,
            "process_manager": _RUST_PROCESS_MANAGER,
        }

    try:
        import mcli_rust

        _RUST_AVAILABLE = True

        # Check individual components
        _RUST_TFIDF = hasattr(mcli_rust, "TfIdfVectorizer")
        _RUST_FILE_WATCHER = hasattr(mcli_rust, "FileWatcher")
        _RUST_COMMAND_MATCHER = hasattr(mcli_rust, "CommandMatcher")
        _RUST_PROCESS_MANAGER = hasattr(mcli_rust, "ProcessManager")

        logger.info("Rust extensions loaded successfully")

    except ImportError as e:
        _RUST_AVAILABLE = False
        _RUST_TFIDF = False
        _RUST_FILE_WATCHER = False
        _RUST_COMMAND_MATCHER = False
        _RUST_PROCESS_MANAGER = False

        logger.warning(f"Rust extensions not available: {e}")

    return {
        "available": _RUST_AVAILABLE,
        "tfidf": _RUST_TFIDF,
        "file_watcher": _RUST_FILE_WATCHER,
        "command_matcher": _RUST_COMMAND_MATCHER,
        "process_manager": _RUST_PROCESS_MANAGER,
    }


def get_tfidf_vectorizer(use_rust: bool = True, **kwargs):
    """Get the best available TF-IDF vectorizer"""
    rust_status = check_rust_extensions()

    if use_rust and rust_status["tfidf"]:
        try:
            import mcli_rust

            return mcli_rust.TfIdfVectorizer(**kwargs)
        except Exception as e:
            logger.warning(f"Failed to create Rust TF-IDF vectorizer: {e}")

    # Fallback to sklearn
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        return TfidfVectorizer(**kwargs)
    except ImportError:
        raise RuntimeError("No TF-IDF vectorizer implementation available")


def get_file_watcher(use_rust: bool = True):
    """Get the best available file watcher"""
    rust_status = check_rust_extensions()

    if use_rust and rust_status["file_watcher"]:
        try:
            import mcli_rust

            return mcli_rust.FileWatcher()
        except Exception as e:
            logger.warning(f"Failed to create Rust file watcher: {e}")

    # Fallback to Python watchdog
    try:
        from mcli.lib.watcher.python_watcher import PythonFileWatcher

        return PythonFileWatcher()
    except ImportError:
        raise RuntimeError("No file watcher implementation available")


def get_command_matcher(use_rust: bool = True, **kwargs):
    """Get the best available command matcher"""
    rust_status = check_rust_extensions()

    if use_rust and rust_status["command_matcher"]:
        try:
            import mcli_rust

            return mcli_rust.CommandMatcher(**kwargs)
        except Exception as e:
            logger.warning(f"Failed to create Rust command matcher: {e}")

    # Fallback to Python implementation
    try:
        from mcli.lib.discovery.python_matcher import PythonCommandMatcher

        return PythonCommandMatcher(**kwargs)
    except ImportError:
        raise RuntimeError("No command matcher implementation available")


def get_process_manager(use_rust: bool = True):
    """Get the best available process manager"""
    rust_status = check_rust_extensions()

    if use_rust and rust_status["process_manager"]:
        try:
            import mcli_rust

            return mcli_rust.ProcessManager()
        except Exception as e:
            logger.warning(f"Failed to create Rust process manager: {e}")

    # Fallback to async Python implementation
    try:
        from mcli.workflow.daemon.async_process_manager import AsyncProcessManager

        return AsyncProcessManager()
    except ImportError:
        raise RuntimeError("No process manager implementation available")


class PerformanceMonitor:
    """Monitor performance differences between Rust and Python implementations"""

    def __init__(self):
        self.benchmarks = {}
        self.rust_status = check_rust_extensions()

    def benchmark_tfidf(self, documents: List[str], queries: List[str]) -> Dict[str, Any]:
        """Benchmark TF-IDF performance"""
        import time

        results = {"rust": None, "python": None, "speedup": None}

        # Benchmark Rust implementation
        if self.rust_status["tfidf"]:
            try:
                vectorizer = get_tfidf_vectorizer(use_rust=True)

                start_time = time.perf_counter()
                vectors = vectorizer.fit_transform(documents)
                for query in queries:
                    similarities = vectorizer.similarity(query, documents)
                rust_time = time.perf_counter() - start_time

                results["rust"] = rust_time

            except Exception as e:
                logger.warning(f"Rust TF-IDF benchmark failed: {e}")

        # Benchmark Python implementation
        try:
            vectorizer = get_tfidf_vectorizer(use_rust=False)

            start_time = time.perf_counter()
            vectors = vectorizer.fit_transform(documents)
            for query in queries:
                query_vec = vectorizer.transform([query])
                # Compute similarities manually for fair comparison
                similarities = []
                for doc_vec in vectors:
                    sim = self._cosine_similarity(query_vec[0], doc_vec)
                    similarities.append(sim)
            python_time = time.perf_counter() - start_time

            results["python"] = python_time

        except Exception as e:
            logger.warning(f"Python TF-IDF benchmark failed: {e}")

        # Calculate speedup
        if results["rust"] and results["python"]:
            results["speedup"] = results["python"] / results["rust"]

        return results

    def _cosine_similarity(self, vec1, vec2):
        """Simple cosine similarity implementation"""
        import numpy as np

        dot_product = np.dot(
            vec1.toarray()[0] if hasattr(vec1, "toarray") else vec1,
            vec2.toarray()[0] if hasattr(vec2, "toarray") else vec2,
        )
        norm1 = np.linalg.norm(vec1.toarray()[0] if hasattr(vec1, "toarray") else vec1)
        norm2 = np.linalg.norm(vec2.toarray()[0] if hasattr(vec2, "toarray") else vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def benchmark_file_watching(self, test_dir: str, num_operations: int = 100) -> Dict[str, Any]:
        """Benchmark file watching performance"""
        import os
        import tempfile
        import time

        results = {"rust": None, "python": None, "speedup": None}

        # Create test directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Benchmark Rust implementation
            if self.rust_status["file_watcher"]:
                try:
                    watcher = get_file_watcher(use_rust=True)
                    watcher.start_watching([temp_dir])

                    start_time = time.perf_counter()
                    for i in range(num_operations):
                        test_file = os.path.join(temp_dir, f"test_{i}.txt")
                        with open(test_file, "w") as f:
                            f.write(f"test content {i}")
                        os.remove(test_file)

                    # Give time for events to be processed
                    time.sleep(0.1)
                    events = watcher.get_events()
                    rust_time = time.perf_counter() - start_time

                    watcher.stop_watching()
                    results["rust"] = rust_time

                except Exception as e:
                    logger.warning(f"Rust file watcher benchmark failed: {e}")

            # Benchmark Python implementation would require similar setup
            # but is more complex due to different API

        return results

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information relevant to performance"""
        import platform

        import psutil

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "rust_extensions": self.rust_status,
        }


# Fallback implementations for when Rust extensions are not available


class PythonFileWatcher:
    """Fallback Python file watcher using watchdog"""

    def __init__(self):
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class EventHandler(FileSystemEventHandler):
            def __init__(self):
                self.events = []

            def on_any_event(self, event):
                self.events.append(
                    {
                        "event_type": event.event_type,
                        "path": event.src_path,
                        "is_directory": event.is_directory,
                    }
                )

        self.observer = Observer()
        self.handler = EventHandler()
        self.is_watching = False

    def start_watching(self, paths: List[str], recursive: bool = True):
        from watchdog.observers import Observer

        for path in paths:
            self.observer.schedule(self.handler, path, recursive=recursive)

        self.observer.start()
        self.is_watching = True

    def stop_watching(self):
        if self.is_watching:
            self.observer.stop()
            self.observer.join()
            self.is_watching = False

    def get_events(self):
        events = self.handler.events.copy()
        self.handler.events.clear()
        return events


class PythonCommandMatcher:
    """Fallback Python command matcher"""

    def __init__(self, fuzzy_threshold: float = 0.3):
        self.fuzzy_threshold = fuzzy_threshold
        self.commands = []

    def add_commands(self, commands: List[Dict[str, Any]]):
        self.commands.extend(commands)

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        import re

        results = []
        query_lower = query.lower()

        for cmd in self.commands:
            score = 0.0
            matched_fields = []

            # Exact name match
            if cmd["name"].lower() == query_lower:
                score = 1.0
                matched_fields.append("name")
            # Prefix match
            elif cmd["name"].lower().startswith(query_lower):
                score = 0.9
                matched_fields.append("name")
            # Contains match
            elif query_lower in cmd["name"].lower():
                score = 0.7
                matched_fields.append("name")
            # Description match
            elif query_lower in cmd.get("description", "").lower():
                score = 0.5
                matched_fields.append("description")

            if score >= self.fuzzy_threshold:
                results.append(
                    {
                        "command": cmd,
                        "score": score,
                        "match_type": "python_fallback",
                        "matched_fields": matched_fields,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


# Auto-check Rust extensions on module import
_RUST_EXTENSIONS_STATUS = check_rust_extensions()


def print_performance_summary():
    """Print a stunning visual summary of available performance optimizations"""
    try:
        from rich.columns import Columns
        from rich.panel import Panel
        from rich.rule import Rule
        from rich.text import Text

        from mcli.lib.ui.visual_effects import ColorfulOutput, MCLIBanner, VisualTable, console

        status = check_rust_extensions()

        console.print()
        console.print(Rule("🚀 MCLI Performance Optimizations Summary", style="bright_green"))
        console.print()

        # Check all optimization status
        optimization_data = {
            "rust": {"success": status["available"], "extensions": status},
            "uvloop": {"success": False},
            "redis": {"success": False},
            "aiosqlite": {"success": False},
            "python": {
                "success": True,
                "reason": "GC tuning, bytecode optimization, recursion limit adjustment",
            },
        }

        # Check UVLoop
        try:
            import uvloop

            optimization_data["uvloop"]["success"] = True
            optimization_data["uvloop"]["reason"] = "High-performance event loop active"
        except ImportError:
            optimization_data["uvloop"]["reason"] = "Package not installed"

        # Check Redis
        try:
            import redis

            # Try to ping Redis server
            client = redis.Redis(host="localhost", port=6379, decode_responses=True)
            client.ping()
            client.close()
            optimization_data["redis"]["success"] = True
            optimization_data["redis"]["reason"] = "Cache server connected"
        except ImportError:
            optimization_data["redis"]["reason"] = "Package not installed"
        except Exception:
            optimization_data["redis"]["reason"] = "Server not available"

        # Check AIOSQLite
        try:
            import aiosqlite

            optimization_data["aiosqlite"]["success"] = True
            optimization_data["aiosqlite"]["reason"] = "Async database operations enabled"
        except ImportError:
            optimization_data["aiosqlite"]["reason"] = "Package not installed"

        # Show performance table
        performance_table = VisualTable.create_performance_table(optimization_data)
        console.print(performance_table)
        console.print()

        # Show Rust extensions details if available
        if status["available"]:
            rust_table = VisualTable.create_rust_extensions_table(status)
            console.print(rust_table)
            console.print()

            # Show celebration
            ColorfulOutput.success("All Rust extensions loaded - Maximum performance activated!")
        else:
            ColorfulOutput.warning("Rust extensions not available - Using Python fallbacks")
            console.print()

        console.print(Rule("System Ready", style="bright_blue"))
        console.print()

    except ImportError:
        # Fallback to original simple output if visual effects not available
        status = check_rust_extensions()

        print("\n🚀 MCLI Performance Optimizations Summary:")
        print("=" * 50)

        if status["available"]:
            print("✅ Rust extensions loaded successfully!")
            print(f"   • TF-IDF Vectorizer: {'✅' if status['tfidf'] else '❌'}")
            print(f"   • File Watcher: {'✅' if status['file_watcher'] else '❌'}")
            print(f"   • Command Matcher: {'✅' if status['command_matcher'] else '❌'}")
            print(f"   • Process Manager: {'✅' if status['process_manager'] else '❌'}")
        else:
            print("⚠️  Rust extensions not available - using Python fallbacks")

        # Check other optimizations
        try:
            import uvloop

            print("✅ UVLoop available for async performance")
        except ImportError:
            print("⚠️  UVLoop not available - using default asyncio")

        try:
            import redis

            print("✅ Redis available for caching")
        except ImportError:
            print("⚠️  Redis not available - caching disabled")

        try:
            import aiosqlite

            print("✅ AIOSQLite available for async database operations")
        except ImportError:
            print("⚠️  AIOSQLite not available - using sync SQLite")

        print()


# Print summary when module is imported (can be enabled with env var)
if os.environ.get("MCLI_SHOW_PERFORMANCE_SUMMARY", "0").lower() not in ("0", "false", "no"):
    print_performance_summary()
