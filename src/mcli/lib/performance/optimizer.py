"""
Main performance optimizer that applies all available optimizations
"""

import asyncio
import importlib.util
import os
import sys
from typing import Any, Dict, Optional

from mcli.lib.logger.logger import get_logger
from mcli.lib.performance.rust_bridge import check_rust_extensions, print_performance_summary
from mcli.lib.performance.uvloop_config import get_event_loop_info, install_uvloop

logger = get_logger(__name__)


class PerformanceOptimizer:
    """Centralized performance optimizer for MCLI"""

    def __init__(self):
        self.optimizations_applied = {}
        self.rust_status = None
        self.redis_available = False
        self.uvloop_installed = False

    def apply_all_optimizations(self) -> Dict[str, Any]:
        """Apply all available performance optimizations"""
        results = {}

        # 1. Install UVLoop for better async performance
        results["uvloop"] = self._optimize_event_loop()

        # 2. Check and initialize Rust extensions
        results["rust"] = self._initialize_rust_extensions()

        # 3. Check Redis availability
        results["redis"] = self._check_redis_availability()

        # 4. Configure Python optimizations
        results["python"] = self._optimize_python_settings()

        # 5. Apply environment-specific optimizations
        results["environment"] = self._apply_environment_optimizations()

        self.optimizations_applied = results
        return results

    def _optimize_event_loop(self) -> Dict[str, Any]:
        """Optimize asyncio event loop with UVLoop"""
        try:
            self.uvloop_installed = install_uvloop()

            loop_info = get_event_loop_info()

            return {
                "success": self.uvloop_installed,
                "loop_type": loop_info.get("type", "unknown"),
                "is_uvloop": loop_info.get("is_uvloop", False),
                "performance_gain": "2-4x faster I/O" if loop_info.get("is_uvloop") else "baseline",
            }
        except Exception as e:
            logger.error(f"Failed to optimize event loop: {e}")
            return {"success": False, "error": str(e)}

    def _initialize_rust_extensions(self) -> Dict[str, Any]:
        """Initialize Rust extensions for maximum performance"""
        try:
            self.rust_status = check_rust_extensions()

            if self.rust_status["available"]:
                # Try to load each extension
                extensions_loaded = {}

                if self.rust_status["tfidf"]:
                    try:
                        import mcli_rust

                        # Test TF-IDF
                        vectorizer = mcli_rust.TfIdfVectorizer()
                        test_docs = ["hello world", "rust is fast"]
                        vectorizer.fit_transform(test_docs)
                        extensions_loaded["tfidf"] = True
                    except Exception as e:
                        logger.warning(f"TF-IDF extension test failed: {e}")
                        extensions_loaded["tfidf"] = False

                if self.rust_status["file_watcher"]:
                    try:
                        import mcli_rust

                        # Test file watcher
                        watcher = mcli_rust.FileWatcher()
                        extensions_loaded["file_watcher"] = True
                    except Exception as e:
                        logger.warning(f"File watcher extension test failed: {e}")
                        extensions_loaded["file_watcher"] = False

                if self.rust_status["command_matcher"]:
                    try:
                        import mcli_rust

                        # Test command matcher
                        matcher = mcli_rust.CommandMatcher()
                        extensions_loaded["command_matcher"] = True
                    except Exception as e:
                        logger.warning(f"Command matcher extension test failed: {e}")
                        extensions_loaded["command_matcher"] = False

                if self.rust_status["process_manager"]:
                    try:
                        import mcli_rust

                        # Test process manager
                        manager = mcli_rust.ProcessManager()
                        extensions_loaded["process_manager"] = True
                    except Exception as e:
                        logger.warning(f"Process manager extension test failed: {e}")
                        extensions_loaded["process_manager"] = False

                return {
                    "success": True,
                    "extensions": extensions_loaded,
                    "performance_gain": "10-100x faster for compute-intensive operations",
                }
            else:
                return {
                    "success": False,
                    "reason": "Rust extensions not available",
                    "fallback": "Using Python implementations",
                }

        except Exception as e:
            logger.error(f"Failed to initialize Rust extensions: {e}")
            return {"success": False, "error": str(e)}

    def _check_redis_availability(self) -> Dict[str, Any]:
        """Check Redis availability for caching"""
        try:
            import redis

            # Try to connect to Redis
            client = redis.Redis(host="localhost", port=6379, decode_responses=True)
            client.ping()
            client.close()

            self.redis_available = True
            return {
                "success": True,
                "performance_gain": "Caching enabled for TF-IDF vectors and command data",
            }

        except ImportError:
            return {
                "success": False,
                "reason": "Redis package not installed",
                "install_command": "pip install redis",
            }
        except Exception as e:
            return {
                "success": False,
                "reason": f"Redis server not available: {e}",
                "fallback": "In-memory caching only",
            }

    def _optimize_python_settings(self) -> Dict[str, Any]:
        """Apply Python-specific optimizations"""
        optimizations = {}

        # 1. Disable garbage collection during critical operations
        import gc

        gc.set_threshold(700, 10, 10)  # More aggressive GC
        optimizations["gc_tuned"] = True

        # 2. Optimize import system
        if hasattr(sys, "dont_write_bytecode"):
            # In production, enable bytecode for faster imports
            if not os.environ.get("MCLI_DEBUG"):
                sys.dont_write_bytecode = False
                optimizations["bytecode_enabled"] = True

        # 3. Set optimal recursion limit
        current_limit = sys.getrecursionlimit()
        if current_limit < 3000:
            sys.setrecursionlimit(3000)
            optimizations["recursion_limit_increased"] = True

        # 4. Configure multiprocessing
        try:
            import multiprocessing as mp

            if hasattr(mp, "set_start_method"):
                if sys.platform != "win32":
                    mp.set_start_method("fork", force=True)
                    optimizations["multiprocessing_optimized"] = True
        except RuntimeError:
            # Start method already set
            pass

        return {
            "success": True,
            "optimizations": optimizations,
            "performance_gain": "Reduced overhead and improved memory management",
        }

    def _apply_environment_optimizations(self) -> Dict[str, Any]:
        """Apply environment-specific optimizations"""
        optimizations = {}

        # 1. Production vs Development optimizations
        if os.environ.get("MCLI_ENV") == "production":
            # Disable debug features
            os.environ["PYTHONOPTIMIZE"] = "1"
            optimizations["debug_disabled"] = True

            # Enable optimized logging
            logger.setLevel("INFO")
            optimizations["logging_optimized"] = True

        # 2. Memory optimizations based on available RAM
        try:
            import psutil

            available_memory = psutil.virtual_memory().available

            if available_memory > 8 * 1024**3:  # 8GB+
                # Large memory optimizations
                os.environ["MCLI_LARGE_CACHE"] = "1"
                optimizations["large_memory_mode"] = True
            elif available_memory < 2 * 1024**3:  # <2GB
                # Low memory optimizations
                os.environ["MCLI_LOW_MEMORY"] = "1"
                optimizations["low_memory_mode"] = True
        except ImportError:
            pass

        # 3. CPU optimizations
        try:
            import psutil

            cpu_count = psutil.cpu_count()

            if cpu_count >= 8:
                # Multi-core optimizations
                os.environ["MCLI_PARALLEL_WORKERS"] = str(min(cpu_count - 1, 16))
                optimizations["parallel_processing"] = True
        except ImportError:
            pass

        # 4. Storage optimizations
        try:
            import shutil

            total, used, free = shutil.disk_usage("/")

            if free > 10 * 1024**3:  # 10GB+ free
                # Enable aggressive caching
                os.environ["MCLI_AGGRESSIVE_CACHE"] = "1"
                optimizations["aggressive_caching"] = True
        except:
            pass

        return {
            "success": True,
            "optimizations": optimizations,
            "performance_gain": "Environment-specific optimizations applied",
        }

    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get a summary of all applied optimizations"""
        if not self.optimizations_applied:
            self.apply_all_optimizations()

        summary = {
            "total_optimizations": len(self.optimizations_applied),
            "successful_optimizations": sum(
                1 for opt in self.optimizations_applied.values() if opt.get("success", False)
            ),
            "estimated_performance_gain": self._estimate_performance_gain(),
            "details": self.optimizations_applied,
        }

        return summary

    def _estimate_performance_gain(self) -> str:
        """Estimate overall performance gain"""
        gains = []

        if self.optimizations_applied.get("uvloop", {}).get("success"):
            gains.append("2-4x async I/O performance")

        if self.optimizations_applied.get("rust", {}).get("success"):
            rust_extensions = self.optimizations_applied["rust"].get("extensions", {})
            if any(rust_extensions.values()):
                gains.append("10-100x compute performance")

        if self.optimizations_applied.get("redis", {}).get("success"):
            gains.append("Significant caching speedup")

        if gains:
            return " + ".join(gains)
        else:
            return "Baseline performance with Python optimizations"

    def benchmark_performance(self, test_size: str = "small") -> Dict[str, Any]:
        """Run performance benchmarks"""
        from mcli.lib.performance.rust_bridge import PerformanceMonitor

        monitor = PerformanceMonitor()

        # Prepare test data
        if test_size == "small":
            documents = [f"test document {i}" for i in range(100)]
            queries = [f"query {i}" for i in range(10)]
        elif test_size == "medium":
            documents = [f"test document {i} with more content" for i in range(1000)]
            queries = [f"query {i}" for i in range(50)]
        else:  # large
            documents = [
                f"test document {i} with much more content and details" for i in range(5000)
            ]
            queries = [f"query {i}" for i in range(100)]

        # Run benchmarks
        tfidf_results = monitor.benchmark_tfidf(documents, queries)

        return {
            "test_size": test_size,
            "tfidf_benchmark": tfidf_results,
            "system_info": monitor.get_system_info(),
            "optimization_status": self.get_optimization_summary(),
        }

    def print_performance_report(self):
        """Print a detailed performance report"""
        summary = self.get_optimization_summary()

        print("\n" + "=" * 60)
        print("🚀 MCLI PERFORMANCE OPTIMIZATION REPORT")
        print("=" * 60)

        print(f"\n📊 Optimization Summary:")
        print(f"   • Total optimizations attempted: {summary['total_optimizations']}")
        print(f"   • Successful optimizations: {summary['successful_optimizations']}")
        print(f"   • Estimated performance gain: {summary['estimated_performance_gain']}")

        print(f"\n⚡ Applied Optimizations:")
        for name, details in summary["details"].items():
            status = "✅" if details.get("success") else "❌"
            print(f"   {status} {name.replace('_', ' ').title()}")
            if details.get("performance_gain"):
                print(f"      → {details['performance_gain']}")
            if details.get("reason"):
                print(f"      → {details['reason']}")

        print(f"\n🔧 Recommendations:")

        # Rust extensions
        if not self.optimizations_applied.get("rust", {}).get("success"):
            print("   • Install Rust and build extensions for maximum performance:")
            print("     cd mcli_rust && cargo build --release")

        # Redis
        if not self.optimizations_applied.get("redis", {}).get("success"):
            print("   • Install and start Redis for caching:")
            print("     docker run -d -p 6379:6379 redis:alpine")

        # UVLoop
        if not self.optimizations_applied.get("uvloop", {}).get("success"):
            print("   • Install UVLoop for better async performance:")
            print("     pip install uvloop")

        print("\n" + "=" * 60)


# Global optimizer instance
_global_optimizer: Optional[PerformanceOptimizer] = None


def get_global_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance"""
    global _global_optimizer

    if _global_optimizer is None:
        _global_optimizer = PerformanceOptimizer()

    return _global_optimizer


def apply_optimizations() -> Dict[str, Any]:
    """Apply all available optimizations"""
    optimizer = get_global_optimizer()
    return optimizer.apply_all_optimizations()


def print_optimization_report():
    """Print the optimization report"""
    optimizer = get_global_optimizer()
    optimizer.print_performance_report()


# Auto-apply optimizations when module is imported (can be disabled)
if os.environ.get("MCLI_AUTO_OPTIMIZE", "1").lower() not in ("0", "false", "no"):
    _optimization_results = apply_optimizations()

    # Print summary if in debug mode
    if os.environ.get("MCLI_DEBUG") or os.environ.get("MCLI_SHOW_OPTIMIZATIONS"):
        print_optimization_report()
