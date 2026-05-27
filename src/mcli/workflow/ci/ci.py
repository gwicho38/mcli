"""`mcli ci` — act-first CI gate and hosted-trigger migration for private repos."""

from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path

import click

from mcli.workflow.ci.act_runner import PreflightResult, act_available, docker_running
from mcli.workflow.ci.act_runner import preflight as preflight_fn
from mcli.workflow.ci.runner_status import has_online_runner
from mcli.workflow.ci.workflow_transform import transform_file, write_self_hosted_workflow

_GITHUB_REMOTE_RE = re.compile(
    r"(?:git@github\.com:|https://github\.com/)([^/]+/[^/]+?)(?:\.git)?/?$"
)


def current_repo_slug() -> str | None:
    """owner/name from a github.com origin remote, or None (non-GitHub or no remote)."""
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if not url:
        return None
    match = _GITHUB_REMOTE_RE.match(url)
    return match.group(1) if match else None


def detect_test_command() -> str:
    """Best-effort test command for the self-hosted fallback workflow."""
    makefile = Path("Makefile")
    if makefile.exists():
        txt = makefile.read_text()
        if "\ntest:" in txt or txt.startswith("test:"):
            return "make test"
    if Path("pyproject.toml").exists() or Path("pytest.ini").exists():
        return "uv run pytest -v || pytest -v"
    if Path("package.json").exists():
        return "npm test"
    if Path("mix.exs").exists():
        return "mix test"
    return "echo 'TODO: set test command' && exit 1"


def workflows_dir() -> Path:
    return Path(".github") / "workflows"


@click.group()
def ci():
    """act-first CI: local act gate + stop billed hosted runners on private repos."""


@ci.command()
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
def migrate(dry_run):
    """Strip hosted triggers from this repo's workflows + add self-hosted fallback."""
    wfdir = workflows_dir()
    if not wfdir.exists():
        click.echo("No .github/workflows directory; nothing to migrate.")
        return
    slug = current_repo_slug()
    has_runner = has_online_runner(slug) if slug else False
    test_cmd = detect_test_command()

    files = sorted(p for p in wfdir.glob("*.y*ml") if p.name != "self-hosted-ci.yml")
    if dry_run:
        from mcli.workflow.ci.workflow_transform import MARKER, _yaml, workflow_has_hosted_job

        for f in files:
            text = f.read_text()
            if MARKER in text:
                click.echo(f"  skip (already migrated): {f.name}")
                continue
            hosted = workflow_has_hosted_job(_yaml().load(text))
            click.echo(f"  {'STRIP' if hosted else 'keep '}: {f.name}")
        click.echo(f"  fallback self-hosted-ci.yml (pull_request={has_runner}, test='{test_cmd}')")
        return

    changed = [f.name for f in files if transform_file(f)]
    created = write_self_hosted_workflow(wfdir, test_cmd, with_pull_request=has_runner)
    for name in changed:
        click.echo(f"  stripped: {name}")
    if created:
        click.echo(f"  created: self-hosted-ci.yml (pull_request={has_runner})")
    click.echo(f"Done. {len(changed)} workflow(s) migrated.")


@ci.command()
@click.option("--event", default="pull_request", show_default=True, help="act event to simulate.")
def preflight(event):
    """Run act as the PR gate. Exit 0=pass, 1=fail, 2=cannot validate, 3=use runner."""
    slug = current_repo_slug()
    result = preflight_fn(slug, event)
    if result == PreflightResult.PASS:
        click.echo("✅ act passed — OK to open PR.")
        raise SystemExit(0)
    if result == PreflightResult.FAIL:
        click.echo("❌ act failed — fix before opening PR.")
        raise SystemExit(1)
    # UNREACHABLE
    if slug and has_online_runner(slug):
        click.echo(
            "⚠️  act unreachable here; an online runner exists — "
            "push and let the self-hosted runner validate."
        )
        raise SystemExit(3)
    click.echo("⚠️  act unreachable and no online runner — cannot validate this PR.")
    raise SystemExit(2)


@ci.command()
def pr():
    """preflight, then `gh pr create --fill --base main` if it passed."""
    slug = current_repo_slug()
    result = preflight_fn(slug)
    if result == PreflightResult.PASS:
        # check=False on purpose: let gh/git stream their own errors to the terminal
        # rather than raising CalledProcessError and hiding their output.
        subprocess.run(["gh", "pr", "create", "--fill", "--base", "main"], check=False)
        return
    if result == PreflightResult.FAIL:
        click.echo("act failed; not opening PR.")
        raise SystemExit(1)
    if slug and has_online_runner(slug):
        click.echo("act unreachable; pushing so the runner can validate.")
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], check=False)
        subprocess.run(["gh", "pr", "create", "--fill", "--base", "main"], check=False)
        return
    click.echo("act unreachable and no runner; refusing to open an unvalidated PR.")
    raise SystemExit(2)


PRE_PUSH_HOOK = """#!/usr/bin/env bash
# mcli-ci pre-push gate: validate with act before pushing.
exec mcli ci preflight
"""


@ci.command()
def doctor():
    """Show act/docker/runner status for this repo."""
    click.echo(f"act installed:  {act_available()}")
    click.echo(f"docker running: {docker_running()}")
    slug = current_repo_slug()
    click.echo(f"repo:           {slug or '(no origin)'}")
    if slug:
        click.echo(f"online runner:  {has_online_runner(slug)}")


@ci.command(name="install-hook")
def install_hook():
    """Install an opt-in pre-push hook that runs `mcli ci preflight`."""
    hooks = Path(".git") / "hooks"
    if not hooks.exists():
        click.echo("Not a git repo (.git/hooks missing).")
        raise SystemExit(1)
    hook = hooks / "pre-push"
    hook.write_text(PRE_PUSH_HOOK)
    mode = hook.stat().st_mode
    hook.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    click.echo(f"Installed pre-push hook at {hook}")
