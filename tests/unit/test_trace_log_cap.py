"""Trace logs stay bounded, and the test suite never writes them to the real home.

On a CI host the suite turned runtime tracing on (tests/unit/test_logger.py)
and never turned it off. sys.settrace is process-wide, so every later test was
traced, line by line, into the user's real ~/.mcli/logs, through a plain
FileHandler with no size limit: 35 GB of mcli_trace_*.log, up to 13 GB a day.
"""

import logging
import os
import sys
import time
from pathlib import Path

import pytest

from mcli.lib.constants.defaults import TraceLogs
from mcli.lib.constants.env import EnvVars


@pytest.fixture
def fresh_logger(tmp_path, monkeypatch):
    """A new McliLogger whose logs go to tmp_path/logs."""
    from mcli.lib.logger.logger import McliLogger

    monkeypatch.setenv(EnvVars.MCLI_HOME, str(tmp_path))
    old = McliLogger._instance
    McliLogger._instance = None

    def make():
        McliLogger._instance = None
        McliLogger._instance = McliLogger("mcli.out")
        return McliLogger._instance

    yield make
    inst = McliLogger._instance
    if inst is not None:
        for lg in (inst.logger, inst.trace_logger, inst.system_trace_logger):
            for h in list(lg.handlers):
                h.close()
                lg.removeHandler(h)
    McliLogger._instance = old


def _trace_bytes(logs_dir: Path) -> int:
    return sum(p.stat().st_size for p in logs_dir.glob("mcli_trace_*.log*"))


def test_the_trace_log_is_capped_by_size(fresh_logger, tmp_path, monkeypatch):
    monkeypatch.setenv(EnvVars.MCLI_TRACE_LOG_MAX_BYTES, "20000")
    log = fresh_logger()
    line = "x" * 100
    for _ in range(3000):  # ~330 KB unbounded
        log.trace_logger.debug(line)
    for h in log.trace_logger.handlers:
        h.flush()
    total = _trace_bytes(tmp_path / "logs")
    assert total <= 20000 * (TraceLogs.BACKUP_COUNT + 1) + 1000, total


def test_the_system_trace_log_is_capped_by_size(fresh_logger, tmp_path, monkeypatch):
    monkeypatch.setenv(EnvVars.MCLI_TRACE_LOG_MAX_BYTES, "20000")
    log = fresh_logger()
    for _ in range(3000):
        log.system_trace_logger.info("y" * 100)
    for h in log.system_trace_logger.handlers:
        h.flush()
    total = sum(p.stat().st_size for p in (tmp_path / "logs").glob("mcli_system_*.log*"))
    assert total <= 20000 * (TraceLogs.BACKUP_COUNT + 1) + 1000, total


def test_old_trace_logs_are_pruned_and_other_logs_are_kept(fresh_logger, tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    old_trace = logs / "mcli_trace_20200101.log"
    old_gz = logs / "mcli_trace_20200102.log.gz"
    old_system = logs / "mcli_system_20200101.log.1"
    old_main = logs / "mcli_20200101.log"
    recent_trace = logs / "mcli_trace_29990101.log"
    for p in (old_trace, old_gz, old_system, old_main, recent_trace):
        p.write_text("data")
    stale = time.time() - (TraceLogs.RETENTION_DAYS + 1) * 86400
    for p in (old_trace, old_gz, old_system, old_main):
        os.utime(p, (stale, stale))

    fresh_logger()

    assert not old_trace.exists()
    assert not old_gz.exists()
    assert not old_system.exists()
    assert old_main.exists(), "the main log is not a trace log"
    assert recent_trace.exists()


def test_no_empty_trace_file_is_created_when_nothing_is_traced(fresh_logger, tmp_path):
    log = fresh_logger()
    log.logger.info("ordinary message")
    assert list((tmp_path / "logs").glob("mcli_trace_*.log")) == []


def test_the_suite_never_logs_to_the_real_home():
    from mcli.lib.paths import get_logs_dir

    real = Path.home() / ".mcli"
    assert real not in get_logs_dir().parents, get_logs_dir()


def test_runtime_tracing_does_not_outlive_the_test_that_enabled_it_part_1():
    from mcli.lib.logger.logger import McliLogger

    McliLogger.enable_runtime_tracing(level=1)
    assert sys.gettrace() is not None


def test_runtime_tracing_does_not_outlive_the_test_that_enabled_it_part_2():
    # Runs after part 1 (same module, file order): the suite's autouse fixture
    # must have switched tracing off in between.
    from mcli.lib.logger.logger import McliLogger

    assert not McliLogger._runtime_tracing_enabled
    assert getattr(sys.gettrace(), "__func__", None) is not McliLogger._trace_callback


def test_trace_logs_on_disk_are_bounded_even_if_tracing_stays_on():
    # Two trace files a day (runtime and system), each at most MAX_BYTES plus
    # BACKUP_COUNT rotated copies, kept for RETENTION_DAYS (plus today).
    per_day = 2 * TraceLogs.MAX_BYTES * (TraceLogs.BACKUP_COUNT + 1)
    worst_case = per_day * (TraceLogs.RETENTION_DAYS + 1)
    assert worst_case <= 3 * 1024**3, worst_case
