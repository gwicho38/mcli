"""Run `act` locally and classify the outcome for the PR gate."""
from __future__ import annotations

import shutil
import subprocess
from enum import Enum
from pathlib import Path


class PreflightResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    UNREACHABLE = "unreachable"


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


def run_act(event: str = "pull_request") -> PreflightResult:
    """Run act for `event`. PASS on exit 0, else FAIL. (Probe gates UNREACHABLE upstream.)"""
    proc = subprocess.run(build_act_command(event))
    return PreflightResult.PASS if proc.returncode == 0 else PreflightResult.FAIL


def preflight(repo_slug: str, event: str = "pull_request") -> PreflightResult:
    """Primary gate. PASS/FAIL if act can run; UNREACHABLE if act can't start here.

    `repo_slug` is accepted for symmetry and future use; the runner fallback is
    orchestrated by the CLI layer based on runner_status.has_online_runner.
    """
    if not probe():
        return PreflightResult.UNREACHABLE
    return run_act(event)
