"""Run `act` locally and classify the outcome for the PR gate."""

from __future__ import annotations

import platform
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

# Canonical CI entrypoint created by `mcli ci migrate`: ci.yml runs on
# `workflow_dispatch`. The job id is NOT fixed (`mcli ci migrate` keeps the
# repo's original job name, e.g. `test`) — so preflight discovers the real job
# id(s) from `act --list` rather than assuming a hardcoded name.
_DISPATCH_WORKFLOW = Path(".github/workflows/ci.yml")

# Header label of the job-id column in `act --list` table output.
_JOB_ID_HEADER = "Job ID"


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


# Preferred over act when present: a repo-defined `make ci-native` target runs
# the same gates directly on the host toolchain. On Apple-silicon (and any host
# without nested-virt) act's amd64 emulation under podman is flaky for heavy
# jobs (container-vanish races, action-clone failures), so a native run is both
# faster and more reliable. Repos opt in simply by defining the target.
_NATIVE_GATE = "ci-native"


def native_gate_available() -> bool:
    """True if the repo defines a `make ci-native` target (preferred over act)."""
    try:
        proc = subprocess.run(
            ["make", "-n", _NATIVE_GATE], capture_output=True, text=True, timeout=30
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_native() -> PreflightResult:
    """Run the repo's native gate (`make ci-native`) on the host. PASS on exit 0,
    FAIL otherwise. Output streams straight to the terminal (these runs are long;
    no need to buffer)."""
    proc = subprocess.run(["make", _NATIVE_GATE])
    return PreflightResult.PASS if proc.returncode == 0 else PreflightResult.FAIL


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


def default_container_arch() -> str | None:
    """`--container-architecture` value for the host, or None to let act decide.

    act's runner images are amd64. On Apple-silicon (darwin/arm64) act warns and
    misbehaves unless told to emulate amd64, so force it; native amd64 Linux
    needs nothing.
    """
    if sys.platform == "darwin" and platform.machine() in ("arm64", "aarch64"):
        return "linux/amd64"
    return None


def dispatch_workflow() -> str | None:
    """The canonical workflow file to drive via `workflow_dispatch`, or None."""
    if _DISPATCH_WORKFLOW.exists():
        return str(_DISPATCH_WORKFLOW)
    return None


def list_jobs(event: str, workflow: str | None = None) -> list[str]:
    """Real job ids act would run for `event`, parsed from the `act --list` table.

    `act --list` prints a table whose first row is a header containing a `Job ID`
    column; each subsequent row is a runnable job. Returns job ids in table order
    (deduplicated). Returns ``[]`` when act lists no jobs for the event (including
    the "could not find any stages" no-op) or when act can't be invoked — never
    raises, so callers can treat an empty result as "nothing to run".
    """
    cmd = ["act", event, "--list"]
    if workflow is not None:
        cmd += ["-W", workflow]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    return _parse_job_ids(proc.stdout or "")


def _parse_job_ids(listing: str) -> list[str]:
    """Extract the `Job ID` column from `act --list` table output."""
    lines = [ln for ln in listing.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0]
    if _JOB_ID_HEADER not in header:
        return []
    # Columns are whitespace-separated; the job id is the second field in act's
    # fixed-order table (Stage, Job ID, Job name, ...).
    col = header.split().index(_JOB_ID_HEADER.split()[1]) - 1
    job_ids: list[str] = []
    for row in lines[1:]:
        fields = row.split()
        if len(fields) > col:
            jid = fields[col]
            if jid not in job_ids:
                job_ids.append(jid)
    return job_ids


def build_act_command(
    event: str,
    workflow: str | None = None,
    job: str | None = None,
    arch: str | None = None,
) -> list[str]:
    cmd = ["act", event]
    if workflow is not None:
        cmd += ["-W", workflow]
    if job is not None:
        cmd += ["-j", job]
    if arch is not None:
        cmd += ["--container-architecture", arch]
    if Path(".secrets").exists():
        cmd += ["--secret-file", ".secrets"]
    return cmd


def _run_with_retries(
    cmd: list[str], retries: int, backoff: tuple[int, ...]
) -> tuple[PreflightResult, str]:
    """Run one act command, retrying on Docker Hub rate limits. Returns the
    classified result plus the combined output (so the caller can detect the
    'no stages' no-op and decide whether to fall back)."""
    attempt = 0
    while True:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        if output:
            sys.stdout.write(output if output.endswith("\n") else output + "\n")

        if proc.returncode == 0:
            return PreflightResult.PASS, output

        # No job matches this event (e.g. workflow_dispatch-only). PASS here is
        # provisional — run_act decides whether a dispatch fallback exists.
        if _has_no_stages(output):
            return PreflightResult.PASS, output

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
            return PreflightResult.UNREACHABLE, output

        return PreflightResult.FAIL, output


def run_act(
    event: str = "pull_request",
    retries: int = _MAX_RETRIES,
    backoff: tuple[int, ...] = _RETRY_BACKOFF,
) -> PreflightResult:
    """Run act for `event` and classify the outcome.

    - exit 0 -> PASS.
    - non-zero whose output shows a Docker Hub pull rate limit
      (``toomanyrequests``) -> retried; if still limited, UNREACHABLE.
    - any other non-zero exit -> FAIL.

    Migrated repos are ``workflow_dispatch``-only, so the default
    ``pull_request`` event matches no jobs. Rather than hollow-pass, fall back
    to the canonical ``ci.yml`` on ``workflow_dispatch``: discover its real job
    id(s) via ``act --list`` (the job name is NOT fixed — ``mcli ci migrate``
    keeps the repo's original name) and run each so the gate validates for real.

    A green result means act actually executed ≥1 job and every job passed. If
    ``act --list`` shows jobs but a run reports "could not find any stages"
    (i.e. act ran nothing), that is a FAILURE, not a no-op — never a hollow pass.
    """
    arch = default_container_arch()
    result, output = _run_with_retries(
        build_act_command(event, arch=arch), retries, backoff
    )

    if not (result == PreflightResult.PASS and _has_no_stages(output)):
        return result

    # No stages for the requested event — try the workflow_dispatch entrypoint.
    workflow = dispatch_workflow()
    if workflow is None:
        sys.stdout.write(
            "ℹ️  No act stages for this event and no ci.yml dispatch "
            "entrypoint — nothing to validate; treating as pass.\n"
        )
        return PreflightResult.PASS

    jobs = list_jobs("workflow_dispatch", workflow)
    if not jobs:
        # The dispatch entrypoint genuinely has no jobs — a real no-op.
        sys.stdout.write(
            f"ℹ️  {workflow} has no workflow_dispatch jobs — nothing to "
            "validate; treating as pass.\n"
        )
        return PreflightResult.PASS

    targets = f"{workflow} {jobs}"
    sys.stdout.write(
        f"ℹ️  No '{event}' stages (workflow_dispatch-only); running "
        f"{targets} via workflow_dispatch…\n"
    )
    for job in jobs:
        result, output = _run_with_retries(
            build_act_command(
                "workflow_dispatch", workflow=workflow, job=job, arch=arch
            ),
            retries,
            backoff,
        )
        if result == PreflightResult.UNREACHABLE:
            return PreflightResult.UNREACHABLE
        # We KNOW this job exists (it came from `act --list`), so "no stages"
        # here means act ran nothing — a failure, not a no-op. Do not pass.
        if result != PreflightResult.PASS or _has_no_stages(output):
            return PreflightResult.FAIL

    return PreflightResult.PASS


def preflight(repo_slug: str, event: str = "pull_request") -> PreflightResult:
    """Primary gate. PASS/FAIL if act can run; UNREACHABLE if act can't start here.

    `repo_slug` is accepted for symmetry and future use; the runner fallback is
    orchestrated by the CLI layer based on runner_status.has_online_runner.

    Prefers a repo-defined native gate (`make ci-native`) over act: it runs the
    same checks on the host toolchain, avoiding act's flaky container emulation.
    """
    if native_gate_available():
        sys.stdout.write(
            "▶ Native CI gate found — running `make ci-native` (no act)…\n"
        )
        return run_native()
    if not probe():
        return PreflightResult.UNREACHABLE
    return run_act(event)
