"""Run `act` locally and classify the outcome for the PR gate."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path

# Docker Hub returns these when the unauthenticated image-pull rate limit is hit.
# act surfaces them while pulling the runner image — this is an environment
# problem, NOT a test failure, so it must not hard-block a push.
_RATE_LIMIT_MARKERS = (
    "toomanyrequests",
    "you have reached your unauthenticated pull rate limit",
    "pull rate limit",
)

# act emits this when no job matches the requested event (e.g. a
# workflow_dispatch-only workflow queried for pull_request). That is a no-op,
# not a failure, so the gate must treat it as PASS rather than block the push.
_NO_STAGES_MARKERS = ("could not find any stages to run",)

# Backoff (seconds) between docker rate-limit retries; the last value repeats.
_RETRY_BACKOFF = (15, 45)
_MAX_RETRIES = 2


class PreflightResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    UNREACHABLE = "unreachable"


def _is_docker_rate_limited(output: str) -> bool:
    low = (output or "").lower()
    return any(marker in low for marker in _RATE_LIMIT_MARKERS)


def _has_no_stages(output: str) -> bool:
    low = (output or "").lower()
    return any(marker in low for marker in _NO_STAGES_MARKERS)


def act_available() -> bool:
    return shutil.which("act") is not None


def docker_running() -> bool:
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, timeout=30)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def probe() -> bool:
    """Can act actually run here? Needs the binary, a live docker daemon, and `act -l`."""
    if not act_available() or not docker_running():
        return False
    try:
        proc = subprocess.run(["act", "-l"], capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def build_act_command(event: str) -> list[str]:
    cmd = ["act", event]
    if Path(".secrets").exists():
        cmd += ["--secret-file", ".secrets"]
    return cmd


def run_act(
    event: str = "pull_request",
    retries: int = _MAX_RETRIES,
    backoff: tuple[int, ...] = _RETRY_BACKOFF,
) -> PreflightResult:
    """Run act for `event` and classify the outcome.

    - exit 0 -> PASS.
    - non-zero whose output shows a Docker Hub pull rate limit
      (``toomanyrequests``) -> retry up to ``retries`` times with backoff;
      if still rate-limited, return UNREACHABLE (cannot validate — an
      environment problem, not a test failure, so the gate must not block).
    - any other non-zero exit -> FAIL.

    Output is captured (to detect the rate limit) and echoed so the user still
    sees act's progress.
    """
    attempt = 0
    while True:
        proc = subprocess.run(build_act_command(event), capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        if output:
            sys.stdout.write(output if output.endswith("\n") else output + "\n")

        if proc.returncode == 0:
            return PreflightResult.PASS

        # No job matches this event (e.g. workflow_dispatch-only) — nothing to
        # validate, so this is a pass, not a gate failure.
        if _has_no_stages(output):
            sys.stdout.write(
                "ℹ️  No act stages for this event (workflow_dispatch-only?); "
                "nothing to validate — treating as pass.\n"
            )
            return PreflightResult.PASS

        if _is_docker_rate_limited(output):
            if attempt < retries:
                delay = backoff[min(attempt, len(backoff) - 1)]
                sys.stdout.write(
                    f"⚠️  Docker Hub rate limit (toomanyrequests); retrying in {delay}s "
                    f"(attempt {attempt + 1}/{retries})…\n"
                )
                time.sleep(delay)
                attempt += 1
                continue
            sys.stdout.write(
                "⚠️  Docker Hub still rate-limited after retries — cannot validate "
                "locally; allowing push (run `mcli ci preflight` again later).\n"
            )
            return PreflightResult.UNREACHABLE

        return PreflightResult.FAIL


def preflight(repo_slug: str, event: str = "pull_request") -> PreflightResult:
    """Primary gate. PASS/FAIL if act can run; UNREACHABLE if act can't start here.

    `repo_slug` is accepted for symmetry and future use; the runner fallback is
    orchestrated by the CLI layer based on runner_status.has_online_runner.
    """
    if not probe():
        return PreflightResult.UNREACHABLE
    return run_act(event)
