"""Unit tests for the machine-wide `act` preflight lock (ci.act_lock).

The point of this lock is that two concurrent `mcli ci preflight` invocations —
one per repo, fired by 16 pre-push hooks on the same machine — must not run act
(and therefore the container runtime) at the same time. So the tests assert
*disjoint critical sections*, not the existence of a lockfile.
"""

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import mcli
from mcli.workflow.ci.act_lock import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    LOCK_PATH_ENV,
    LOCK_TIMEOUT_ENV,
    act_lock,
    lock_path,
    resolve_timeout,
)
from mcli.workflow.ci.act_runner import PreflightResult, preflight

_SRC = str(Path(mcli.__file__).resolve().parents[1])

# Child process: take the lock, record the wall-clock window it held it for.
_HOLD_WORKER = """
import sys, time
sys.path.insert(0, {src!r})
from pathlib import Path
from mcli.workflow.ci.act_lock import act_lock

lock, out, hold = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])
with act_lock(timeout=60, path=lock, announce=lambda msg: None) as acquired:
    if not acquired:
        out.write_text("TIMEOUT")
        raise SystemExit(9)
    start = time.time()
    time.sleep(hold)
    out.write_text("{{}} {{}}".format(start, time.time()))
""".format(
    src=_SRC
)

# Child process: take the lock and then hang forever, so the parent can SIGKILL it.
_WEDGE_WORKER = """
import sys, time
sys.path.insert(0, {src!r})
from pathlib import Path
from mcli.workflow.ci.act_lock import act_lock

lock, ready = Path(sys.argv[1]), Path(sys.argv[2])
with act_lock(timeout=60, path=lock, announce=lambda msg: None) as acquired:
    assert acquired
    ready.write_text("held")
    time.sleep(600)
""".format(
    src=_SRC
)


def _spawn(script: str, *args: str) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", script, *[str(a) for a in args]])


def _window(path: Path) -> tuple[float, float]:
    text = path.read_text().strip()
    assert text != "TIMEOUT", "child timed out waiting for the lock"
    start, end = text.split()
    return float(start), float(end)


class TestCrossProcessExclusion:
    def test_two_processes_never_overlap(self, tmp_path):
        """The load-bearing test: two concurrent holders must not overlap."""
        lock = tmp_path / "act.lock"
        out_a, out_b = tmp_path / "a.txt", tmp_path / "b.txt"
        hold = 1.0

        proc_a = _spawn(_HOLD_WORKER, lock, out_a, hold)
        proc_b = _spawn(_HOLD_WORKER, lock, out_b, hold)
        assert proc_a.wait(timeout=90) == 0
        assert proc_b.wait(timeout=90) == 0

        a_start, a_end = _window(out_a)
        b_start, b_end = _window(out_b)
        assert (
            a_end <= b_start or b_end <= a_start
        ), f"critical sections overlapped: A=[{a_start}, {a_end}] B=[{b_start}, {b_end}]"


class TestSerialisedPreflight:
    def test_concurrent_preflights_do_not_run_act_at_once(self, tmp_path, monkeypatch):
        monkeypatch.setenv(LOCK_PATH_ENV, str(tmp_path / "act.lock"))
        live = 0
        peak = 0
        guard = threading.Lock()

        def fake_run_act(event="pull_request"):
            nonlocal live, peak
            with guard:
                live += 1
                peak = max(peak, live)
            time.sleep(0.2)
            with guard:
                live -= 1
            return PreflightResult.PASS

        results: list[PreflightResult] = []

        def call():
            results.append(preflight("o/r"))

        # Patch once, around every thread: entering/exiting mock.patch per thread
        # would let one thread restore the real run_act while another is mid-call.
        with (
            patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=False),
            patch("mcli.workflow.ci.act_runner.probe", return_value=True),
            patch("mcli.workflow.ci.act_runner.run_act", side_effect=fake_run_act),
        ):
            threads = [threading.Thread(target=call) for _ in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=60)

        assert results == [PreflightResult.PASS] * 3
        assert peak == 1, f"{peak} act runs overlapped; the lock did not serialise them"


class TestTimeout:
    def test_timeout_returns_false_without_hanging(self, tmp_path):
        lock = tmp_path / "act.lock"
        with act_lock(timeout=60, path=lock, announce=lambda msg: None) as held:
            assert held is True
            started = time.monotonic()
            with act_lock(timeout=0.3, path=lock, announce=lambda msg: None) as second:
                assert second is False
            assert time.monotonic() - started < 15

    def test_wait_message_names_the_holder(self, tmp_path):
        lock = tmp_path / "act.lock"
        messages: list[str] = []
        with act_lock(timeout=60, path=lock, announce=lambda msg: None):
            with act_lock(timeout=0.3, path=lock, announce=messages.append):
                pass
        assert messages, "waiting produced no message"
        assert str(os.getpid()) in messages[0]

    def test_default_timeout_is_600_seconds(self):
        assert DEFAULT_LOCK_TIMEOUT_SECONDS == 600

    def test_resolve_timeout_precedence(self, monkeypatch):
        monkeypatch.delenv(LOCK_TIMEOUT_ENV, raising=False)
        assert resolve_timeout(None) == DEFAULT_LOCK_TIMEOUT_SECONDS
        monkeypatch.setenv(LOCK_TIMEOUT_ENV, "42")
        assert resolve_timeout(None) == 42
        assert resolve_timeout(5) == 5  # explicit beats env
        monkeypatch.setenv(LOCK_TIMEOUT_ENV, "not-a-number")
        assert resolve_timeout(None) == DEFAULT_LOCK_TIMEOUT_SECONDS


class TestStaleness:
    def test_lock_released_after_exception(self, tmp_path):
        lock = tmp_path / "act.lock"
        try:
            with act_lock(timeout=60, path=lock, announce=lambda msg: None):
                raise RuntimeError("act blew up")
        except RuntimeError:
            pass
        with act_lock(timeout=0, path=lock, announce=lambda msg: None) as held:
            assert held is True

    def test_sigkilled_holder_does_not_wedge_next_caller(self, tmp_path):
        lock = tmp_path / "act.lock"
        ready = tmp_path / "ready.txt"
        proc = _spawn(_WEDGE_WORKER, lock, ready)
        deadline = time.monotonic() + 60
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready.exists(), "child never acquired the lock"

        # Precondition: while the child lives the lock is genuinely held, so the
        # post-kill acquisition below proves the kernel released it.
        with act_lock(timeout=0, path=lock, announce=lambda msg: None) as blocked:
            assert blocked is False

        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=30)

        with act_lock(timeout=10, path=lock, announce=lambda msg: None) as held:
            assert held is True, "a SIGKILLed holder wedged the lock"


class TestLockPath:
    def test_lock_path_is_machine_wide_not_per_repo(self, tmp_path, monkeypatch):
        monkeypatch.delenv(LOCK_PATH_ENV, raising=False)
        monkeypatch.chdir(tmp_path)
        first = lock_path()
        (tmp_path / "other").mkdir()
        monkeypatch.chdir(tmp_path / "other")
        assert lock_path() == first

    def test_lock_path_env_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv(LOCK_PATH_ENV, str(tmp_path / "custom.lock"))
        assert lock_path() == tmp_path / "custom.lock"


class TestPreflightIntegration:
    def test_lock_timeout_is_unreachable_and_skips_act(self, tmp_path, monkeypatch):
        lock = tmp_path / "act.lock"
        monkeypatch.setenv(LOCK_PATH_ENV, str(lock))
        with act_lock(timeout=60, path=lock, announce=lambda msg: None):
            with (
                patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=False),
                patch("mcli.workflow.ci.act_runner.probe", return_value=True),
                patch("mcli.workflow.ci.act_runner.run_act") as run_act,
            ):
                result = preflight("o/r", lock_timeout=0.3)
        assert result == PreflightResult.UNREACHABLE
        run_act.assert_not_called()

    def test_native_gate_is_not_serialised_by_the_act_lock(self, tmp_path, monkeypatch):
        """The native gate is host-local (no container runtime), so it must run
        even while another repo holds the act lock."""
        lock = tmp_path / "act.lock"
        monkeypatch.setenv(LOCK_PATH_ENV, str(lock))
        with act_lock(timeout=60, path=lock, announce=lambda msg: None):
            with (
                patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=True),
                patch(
                    "mcli.workflow.ci.act_runner.run_native",
                    return_value=PreflightResult.PASS,
                ) as run_native,
            ):
                result = preflight("o/r", lock_timeout=0.3)
        assert result == PreflightResult.PASS
        run_native.assert_called_once()

    def test_probe_failure_does_not_wait_on_the_lock(self, tmp_path, monkeypatch):
        """UNREACHABLE from a dead docker must be immediate, not a 600s wait."""
        lock = tmp_path / "act.lock"
        monkeypatch.setenv(LOCK_PATH_ENV, str(lock))
        with act_lock(timeout=60, path=lock, announce=lambda msg: None):
            started = time.monotonic()
            with (
                patch("mcli.workflow.ci.act_runner.native_gate_available", return_value=False),
                patch("mcli.workflow.ci.act_runner.probe", return_value=False),
            ):
                result = preflight("o/r", lock_timeout=30)
            assert time.monotonic() - started < 5
        assert result == PreflightResult.UNREACHABLE
