"""
UVLoop configuration for enhanced asyncio performance
"""

import asyncio
import os
import sys
from typing import Optional


def install_uvloop(force: bool = False) -> bool:
    """
    Install uvloop as the default event loop policy for better performance.

    Args:
        force: Force installation even on non-Unix systems

    Returns:
        True if uvloop was successfully installed, False otherwise
    """
    # Check if uvloop should be used
    if not should_use_uvloop() and not force:
        return False

    try:
        import uvloop

        # Install uvloop as the default event loop policy
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        # Verify installation
        loop = asyncio.new_event_loop()
        is_uvloop = "uvloop" in str(type(loop))
        loop.close()

        if is_uvloop:
            # Only print if explicitly requested
            if os.environ.get("MCLI_VERBOSE_UVLOOP", "0").lower() in ("1", "true", "yes"):
                print("✓ UVLoop installed successfully for enhanced async performance")
            return True
        else:
            if os.environ.get("MCLI_VERBOSE_UVLOOP", "0").lower() in ("1", "true", "yes"):
                print("⚠ UVLoop installation failed - using default asyncio")
            return False

    except ImportError:
        if os.environ.get("MCLI_VERBOSE_UVLOOP", "0").lower() in ("1", "true", "yes"):
            print("⚠ UVLoop not available - install with: pip install uvloop")
        return False
    except Exception as e:
        if os.environ.get("MCLI_VERBOSE_UVLOOP", "0").lower() in ("1", "true", "yes"):
            print(f"⚠ UVLoop installation failed: {e}")
        return False


def should_use_uvloop() -> bool:
    """
    Determine if uvloop should be used based on platform and environment.

    Returns:
        True if uvloop should be used, False otherwise
    """
    # Only use uvloop on Unix-like systems
    if sys.platform not in ("linux", "darwin"):
        return False

    # Check environment variable override
    disable_uvloop = os.environ.get("MCLI_DISABLE_UVLOOP", "").lower()
    if disable_uvloop in ("1", "true", "yes"):
        return False

    # Check if we're in certain environments where uvloop might cause issues
    if is_jupyter_environment():
        return False

    return True


def is_jupyter_environment() -> bool:
    """Check if running in Jupyter/IPython environment."""
    try:
        import IPython

        return IPython.get_ipython() is not None
    except ImportError:
        return False


def get_event_loop_info() -> dict:
    """Get information about the current event loop."""
    try:
        loop = asyncio.get_running_loop()
        loop_type = str(type(loop))

        info = {
            "type": loop_type,
            "is_uvloop": "uvloop" in loop_type,
            "is_running": True,
            "debug": loop.get_debug(),
        }

        # Get additional uvloop-specific info if available
        if hasattr(loop, "_csock"):
            info["uvloop_version"] = getattr(loop, "_uvloop_version", "unknown")

        return info

    except RuntimeError:
        return {"type": "No running loop", "is_uvloop": False, "is_running": False, "debug": False}


def configure_event_loop_for_performance():
    """Configure the event loop for optimal performance."""
    try:
        loop = asyncio.get_running_loop()

        # Disable debug mode in production
        if not os.environ.get("MCLI_DEBUG"):
            loop.set_debug(False)

        # Set task factory for better performance monitoring if needed
        if os.environ.get("MCLI_MONITOR_TASKS"):
            loop.set_task_factory(create_monitored_task)

    except RuntimeError:
        # No running loop - configuration will apply to next loop
        pass


def create_monitored_task(loop, coro):
    """Custom task factory for monitoring task performance."""
    import time

    class MonitoredTask(asyncio.Task):
        def __init__(self, coro, *, loop=None):
            super().__init__(coro, loop=loop)
            self._start_time = time.perf_counter()

        def _step(self, exc=None):
            start = time.perf_counter()
            try:
                result = super()._step(exc)
                return result
            finally:
                duration = time.perf_counter() - start
                if duration > 0.1:  # Log slow operations
                    print(f"Slow task step: {self.get_name()} took {duration:.3f}s")

    return MonitoredTask(coro, loop=loop)


# Auto-install uvloop when module is imported (can be disabled with env var)
if os.environ.get("MCLI_AUTO_UVLOOP", "1").lower() not in ("0", "false", "no"):
    install_uvloop()
