"""MCLI releases only the interpreter hooks it installed."""

import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcli.lib.logger.logger import McliLogger

pytestmark = pytest.mark.unit


@pytest.fixture
def tracing_hooks(monkeypatch):
    original_system = sys.gettrace()
    original_threads = threading.gettrace()

    def external(frame, event, arg):
        return external

    def mcli_hook(frame, event, arg):
        return mcli_hook

    def newer(frame, event, arg):
        return newer

    monkeypatch.setattr(
        McliLogger, "_instance", SimpleNamespace(_trace_callback=mcli_hook, trace_logger=Mock())
    )
    monkeypatch.setattr(McliLogger, "_runtime_tracing_enabled", False)
    sys.settrace(external)
    threading.settrace(external)
    try:
        yield external, mcli_hook, newer
    finally:
        if McliLogger._runtime_tracing_enabled:
            McliLogger.disable_runtime_tracing()
        sys.settrace(original_system)
        threading.settrace(original_threads)


def test_disabling_without_ownership_preserves_external_hooks(tracing_hooks):
    external, _, _ = tracing_hooks
    McliLogger.disable_runtime_tracing()
    assert sys.gettrace() is external
    assert threading.gettrace() is external


def test_repeated_enable_and_disable_restore_prior_hooks(tracing_hooks):
    external, owned, _ = tracing_hooks
    for _ in range(2):
        McliLogger.enable_runtime_tracing(1)
        assert sys.gettrace() is owned
        assert threading.gettrace() is owned
        McliLogger.enable_runtime_tracing(2)
        McliLogger.disable_runtime_tracing()
        assert sys.gettrace() is external
        assert threading.gettrace() is external
        McliLogger.disable_runtime_tracing()
        assert sys.gettrace() is external
        assert threading.gettrace() is external


@pytest.mark.parametrize(
    "replace_system, replace_threads", [(True, False), (False, True), (True, True)]
)
def test_disable_does_not_replace_a_newer_tracers_hooks(
    tracing_hooks, replace_system, replace_threads
):
    external, _, newer = tracing_hooks
    McliLogger.enable_runtime_tracing()
    if replace_system:
        sys.settrace(newer)
    if replace_threads:
        threading.settrace(newer)
    McliLogger.disable_runtime_tracing()
    assert sys.gettrace() is (newer if replace_system else external)
    assert threading.gettrace() is (newer if replace_threads else external)
