"""
Performance optimization utilities for mcli
"""

from .uvloop_config import (
    configure_event_loop_for_performance,
    get_event_loop_info,
    install_uvloop,
    should_use_uvloop,
)

__all__ = [
    "install_uvloop",
    "should_use_uvloop",
    "get_event_loop_info",
    "configure_event_loop_for_performance",
]
