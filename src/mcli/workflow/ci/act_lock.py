"""Machine-wide advisory lock that serialises `mcli ci preflight` act runs.

Every repo that ran `mcli ci install-hook` fires `mcli ci preflight` from its
pre-push hook. With several agents (or several terminals) pushing at once, that
starts several `act` runs at once, and each one drives the same container
runtime — one podman/docker VM with a fixed CPU/memory budget shared with
everything else on the host. Concurrent runs starve it; the observed symptom was
an Android emulator ANR'ing under test while act runs churned.

This module gives the act path a single machine-wide gate:

* Exclusion is `fcntl.flock(LOCK_EX)` on a lockfile in the mcli home. flock is
  owned by the open file description, so the kernel drops it when the holder
  exits — normally, by exception, or by SIGKILL. There is nothing to clean up
  and nothing to go stale.
* The PID/repo written into the lockfile is *informational only*: it makes the
  "waiting for…" message useful. Correctness never reads it.
* Waiting is bounded. On expiry the caller is told it did not get the lock and
  decides what to do — a gate that can block a push forever is worse than one
  that occasionally cannot validate.
"""

from __future__ import annotations

import errno
import fcntl
import os
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable

from mcli.lib.paths import get_mcli_home

# Ten minutes: long enough for a slow act run ahead of us to finish, short
# enough that a wedged machine never holds a push hostage for a workday.
DEFAULT_LOCK_TIMEOUT_SECONDS = 600.0

LOCK_TIMEOUT_ENV = "MCLI_CI_LOCK_TIMEOUT"
LOCK_PATH_ENV = "MCLI_CI_LOCK_PATH"

_LOCK_DIR_NAME = "locks"
_LOCK_FILE_NAME = "ci-act.lock"

# Retry cadence while waiting. flock's blocking mode cannot be bounded
# portably, so poll the non-blocking variant instead.
_POLL_INTERVAL_SECONDS = 0.5

_UNKNOWN_HOLDER = "holder unknown"


def lock_path() -> Path:
    """The one lockfile every repo on this machine contends for.

    Deliberately NOT per-repo: the resource being protected is the host's
    container runtime, which every repo shares.
    """
    override = os.getenv(LOCK_PATH_ENV)
    if override:
        return Path(override)
    return get_mcli_home() / _LOCK_DIR_NAME / _LOCK_FILE_NAME


def resolve_timeout(timeout: float | None = None) -> float:
    """Explicit argument beats `MCLI_CI_LOCK_TIMEOUT` beats the 600s default.

    An unparsable env value falls back to the default rather than raising: a
    typo in a shell profile must not break every push on the machine.
    """
    if timeout is not None:
        return float(timeout)
    raw = os.getenv(LOCK_TIMEOUT_ENV)
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return DEFAULT_LOCK_TIMEOUT_SECONDS


def _write_holder(handle) -> None:
    """Record who holds the lock. Informational only — never load-bearing."""
    try:
        os.ftruncate(handle.fileno(), 0)
        handle.seek(0)
        stamp = datetime.now().isoformat(timespec="seconds")
        handle.write(f"pid={os.getpid()} repo={os.getcwd()} since={stamp}\n")
        handle.flush()
    except OSError:
        pass  # metadata is a nicety; never fail a run over it


def _holder_description(path: Path) -> str:
    """Best-effort description of the current holder, for the wait message."""
    try:
        text = path.read_text().strip()
    except OSError:
        return _UNKNOWN_HOLDER
    return text.splitlines()[0] if text else _UNKNOWN_HOLDER


@contextmanager
def act_lock(
    timeout: float | None = None,
    path: Path | None = None,
    announce: Callable[[str], object] | None = None,
) -> Iterator[bool]:
    """Hold the machine-wide act lock for the duration of the block.

    Yields True when the lock was acquired and False when the wait timed out —
    it never raises on contention, so the caller stays in control of what a
    missed lock means.
    """
    wait_budget = resolve_timeout(timeout)
    lockfile = path if path is not None else lock_path()
    emit = announce if announce is not None else sys.stdout.write

    try:
        lockfile.parent.mkdir(parents=True, exist_ok=True)
        handle = open(lockfile, "a+")
    except OSError as exc:
        # Read-only home, a lockfile owned by another user, no space… none of
        # that is a reason to fail a push. Degrade to the pre-lock behaviour
        # (unserialised) and say so, rather than raising into the gate — an
        # exception here would exit 1 and BLOCK the push in every repo.
        emit(
            f"⚠️  Cannot use the machine-wide act lock at {lockfile} ({exc}); "
            "running act unserialised.\n"
        )
        yield True
        return

    acquired = False
    try:
        deadline = time.monotonic() + wait_budget
        announced = False
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
                    raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if not announced:
                emit(
                    f"⏳ Another `mcli ci preflight` is already running act "
                    f"({_holder_description(lockfile)}); waiting up to "
                    f"{wait_budget:.0f}s for the machine-wide CI lock…\n"
                )
                announced = True
            time.sleep(min(_POLL_INTERVAL_SECONDS, remaining))

        if acquired:
            _write_holder(handle)
        yield acquired
    finally:
        # Closing the descriptor releases the flock by itself; unlocking first
        # is belt-and-braces in case the handle ever outlives this frame.
        if acquired:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()
