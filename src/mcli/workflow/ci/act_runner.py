"""Run `act` locally and classify the outcome for the PR gate."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path

from mcli.workflow.ci.act_lock import LOCK_TIMEOUT_ENV, act_lock, resolve_timeout

# Docker Hub returns these when the unauthenticated image-pull rate limit is hit.
# act surfaces them while pulling the runner image — this is an environment
# problem, NOT a test failure, so it must not hard-block a push.
_RATE_LIMIT_MARKERS = (
    "toomanyrequests",
    "you have reached your unauthenticated pull rate limit",
    "pull rate limit",
)

# act emits this when no job matches the requested event (e.g. a
# workflow_dispatch-only workflow queried for pull_request). That is not a
# failure (it must not block the push, #205), but it is not a pass either:
# run_act falls back to workflow_dispatch gates, and reports NOT_VALIDATED when
# no job ran at all (#242).
_NO_STAGES_MARKERS = ("could not find any stages to run",)

# Backoff (seconds) between docker rate-limit retries; the last value repeats.
_RETRY_BACKOFF = (15, 45)
_MAX_RETRIES = 2

# Dispatch-only workflows that are safe and expected to run as local gates.
# A workflow file is a gate when its stem (split on "-", "_", ".") has a gate
# token and no side-effect token. Deploy, release, publish, build and audit
# workflows are never selected; neither is the dormant self-hosted fallback.
_WORKFLOW_DIR = Path(".github/workflows")
_DISPATCH_GATE_TOKENS = frozenset(
    {"ci", "test", "tests", "lint", "typecheck", "check", "checks", "scan", "security", "quality"}
)
_DISPATCH_SKIP_TOKENS = frozenset(
    {"deploy", "release", "publish", "build", "audit", "ops", "upload", "notify", "sync"}
)
_DISPATCH_SKIP_STEMS = frozenset({"self-hosted-ci"})

# Header label of the job-id column in `act --list` table output.
_JOB_ID_HEADER = "Job ID"


def _act_command(*args: str) -> list[str]:
    """Build an act command without implicitly loading the repository .env."""
    return ["act", *args, "--env-file", os.devnull]


class PreflightResult(Enum):
    PASS = "pass"  # act ran >=1 job and every job passed
    FAIL = "fail"
    UNREACHABLE = "unreachable"  # act cannot run here
    NOT_VALIDATED = "not_validated"  # act ran, but no job matched: nothing validated


def _is_docker_rate_limited(output: str) -> bool:
    low = (output or "").lower()
    return any(marker in low for marker in _RATE_LIMIT_MARKERS)


def _has_no_stages(output: str) -> bool:
    low = (output or "").lower()
    return any(marker in low for marker in _NO_STAGES_MARKERS)


def act_available() -> bool:
    return shutil.which("act") is not None


# Git exports these to every hook (`git rev-parse --local-env-vars`). They point
# at the repo being pushed, so a tool inside the gate that runs git on its own
# checkout reads the wrong repo: Flutter computes its SDK version with
# `git describe` and reports the pushed commit, which then fails any
# `environment: flutter:` constraint. The gate runs from the repo root, so
# git finds the right repo without them.
_GIT_HOOK_ENV = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE",
    "GIT_PREFIX",
    "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR",
)


def _gate_env() -> dict[str, str]:
    """The current environment without the repo-local variables git sets for hooks."""
    return {k: v for k, v in os.environ.items() if k not in _GIT_HOOK_ENV}


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
    proc = subprocess.run(["make", _NATIVE_GATE], env=_gate_env())
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
        proc = subprocess.run(_act_command("-l"), capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def default_container_arch() -> str | None:
    """`--container-architecture` value for the host, or None to let act decide.

    On Apple Silicon, select native arm64 together with the multi-arch runner
    mapping added by build_act_command; native Linux needs no override.
    """
    if sys.platform == "darwin" and platform.machine() in ("arm64", "aarch64"):
        return "linux/arm64"
    return None


def _is_dispatch_gate(stem: str) -> bool:
    """True if a workflow file stem names a check (ci/test/lint/scan…), not a
    deploy/release/publish/build job."""
    stem = stem.lower()
    if stem in _DISPATCH_SKIP_STEMS:
        return False
    tokens = set(re.split(r"[-_.]", stem))
    return bool(tokens & _DISPATCH_GATE_TOKENS) and not tokens & _DISPATCH_SKIP_TOKENS


def dispatch_workflows() -> list[str]:
    """Return dispatch-only check workflows safe to run locally, sorted by path.

    The act-first migration preserved workflow filenames, so a real gate may be
    ``elixir-ci.yml``, ``test.yml`` or ``lint.yml`` rather than ``ci.yml``.
    Select by name token (see ``_DISPATCH_GATE_TOKENS``), and never select a
    deploy/release/publish/build workflow or the dormant self-hosted fallback.
    """
    if not _WORKFLOW_DIR.is_dir():
        return []
    paths = sorted((*_WORKFLOW_DIR.glob("*.yml"), *_WORKFLOW_DIR.glob("*.yaml")))
    return [str(path) for path in paths if _is_dispatch_gate(path.stem)]


def list_jobs(event: str, workflow: str | None = None) -> list[str] | None:
    """Real job ids act would run for `event`, parsed from the `act --list` table.

    `act --list` prints a table whose first row is a header containing a `Job ID`
    column; each subsequent row is a runnable job. Returns job ids in table order
    (deduplicated). Returns ``[]`` when act lists no jobs for the event (including
    the "could not find any stages" no-op). Returns ``None`` when act cannot be
    invoked or listing fails, so callers cannot mistake an error for a green
    workflow with no jobs.
    """
    cmd = _act_command(event, "--list")
    if workflow is not None:
        cmd += ["-W", workflow]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return [] if _has_no_stages(output) else None
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
    cmd = _act_command(event)
    if workflow is not None:
        cmd += ["-W", workflow]
    if job is not None:
        cmd += ["-j", job]
    if arch is not None:
        cmd += ["--container-architecture", arch]
        if arch == "linux/arm64":
            # Use act's full multi-arch runner on Apple Silicon. Emulating BEAM
            # and Dialyzer under QEMU is resource-heavy and prone to
            # compiler/PLT segfaults.
            cmd += ["--env", "RUNNER_ARCH=ARM64"]
            cmd += ["-P", "ubuntu-latest=catthehacker/ubuntu:act-20.04"]
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
        proc = subprocess.run(cmd, capture_output=True, text=True, env=_gate_env())
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
    ``pull_request`` event matches no jobs. Rather than hollow-pass, discover
    check workflows (ci/test/lint/scan…, see ``dispatch_workflows``) and run
    their real job ids via ``workflow_dispatch``. Deploy, release, publish and
    build workflows are never selected.

    A green result means act actually executed ≥1 job and every job passed. If
    ``act --list`` shows jobs but a run reports "could not find any stages"
    (i.e. act ran nothing), that is a FAILURE. If no job matched the event and
    no dispatch gate has a job, the result is NOT_VALIDATED — never PASS (#242).
    """
    arch = default_container_arch()
    result, output = _run_with_retries(build_act_command(event, arch=arch), retries, backoff)

    if not (result == PreflightResult.PASS and _has_no_stages(output)):
        return result

    # No stages for the requested event — try safe workflow_dispatch gates.
    workflows = dispatch_workflows()
    if not workflows:
        sys.stdout.write(
            f"⚠️  No '{event}' jobs and no ci/test/lint/scan workflow_dispatch "
            "workflow — nothing was validated.\n"
        )
        return PreflightResult.NOT_VALIDATED

    ran_job = False
    for workflow in workflows:
        jobs = list_jobs("workflow_dispatch", workflow)
        if jobs is None:
            sys.stdout.write(
                f"❌ Failed to discover workflow_dispatch jobs for {workflow}; "
                "the gate was not executed.\n"
            )
            return PreflightResult.FAIL
        if not jobs:
            sys.stdout.write(f"ℹ️  {workflow} has no workflow_dispatch jobs — skipping.\n")
            continue

        sys.stdout.write(
            f"ℹ️  No '{event}' stages (workflow_dispatch-only); running "
            f"{workflow} {jobs} via workflow_dispatch…\n"
        )
        for job in jobs:
            ran_job = True
            result, output = _run_with_retries(
                build_act_command("workflow_dispatch", workflow=workflow, job=job, arch=arch),
                retries,
                backoff,
            )
            if result == PreflightResult.UNREACHABLE:
                return PreflightResult.UNREACHABLE
            # We KNOW this job exists (it came from `act --list`), so "no stages"
            # here means act ran nothing — a failure, not a no-op. Do not pass.
            if result != PreflightResult.PASS or _has_no_stages(output):
                return PreflightResult.FAIL

    if not ran_job:
        sys.stdout.write(
            f"⚠️  No '{event}' jobs, and {', '.join(workflows)} "
            "have no workflow_dispatch jobs — nothing was validated.\n"
        )
        return PreflightResult.NOT_VALIDATED

    return PreflightResult.PASS


def preflight(
    repo_slug: str, event: str = "pull_request", lock_timeout: float | None = None
) -> PreflightResult:
    """Primary gate. PASS/FAIL if act can run; UNREACHABLE if act can't start here;
    NOT_VALIDATED if act ran but no job matched (nothing was validated).

    `repo_slug` is accepted for symmetry and future use; the runner fallback is
    orchestrated by the CLI layer based on runner_status.has_online_runner.

    Prefers a repo-defined native gate (`make ci-native`) over act: it runs the
    same checks on the host toolchain, avoiding act's flaky container emulation.

    The act run — and only the act run — is serialised machine-wide by
    `act_lock`, because every repo's act run drives the same container runtime.
    The native gate is host-local and stays unlocked, and `probe()` runs before
    the wait so a dead docker is UNREACHABLE immediately instead of after
    `lock_timeout` seconds. On lock timeout the gate reports UNREACHABLE (the
    established "cannot validate" state) rather than starting the second
    concurrent container run this lock exists to prevent.
    """
    if native_gate_available():
        sys.stdout.write("▶ Native CI gate found — running `make ci-native` (no act)…\n")
        return run_native()
    if not probe():
        return PreflightResult.UNREACHABLE
    with act_lock(timeout=lock_timeout) as acquired:
        if not acquired:
            sys.stdout.write(
                f"⚠️  Timed out after {resolve_timeout(lock_timeout):.0f}s waiting for the "
                "machine-wide act lock — another `mcli ci preflight` is still running act. "
                "Refusing to start a second concurrent container run; this push was NOT "
                "validated locally (re-run `mcli ci preflight` when the machine is idle, "
                f"or raise the wait with --lock-timeout / {LOCK_TIMEOUT_ENV}).\n"
            )
            return PreflightResult.UNREACHABLE
        return run_act(event)
