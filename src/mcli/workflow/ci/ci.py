"""`mcli ci` — act-first CI gate and hosted-trigger migration for private repos."""
from __future__ import annotations

import subprocess
from pathlib import Path

import click

from mcli.workflow.ci.workflow_transform import transform_file, write_self_hosted_workflow
from mcli.workflow.ci.runner_status import has_online_runner
from mcli.workflow.ci.act_runner import PreflightResult, preflight


def current_repo_slug() -> str | None:
    """owner/name from the origin remote, or None."""
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if not url:
        return None
    url = url.removesuffix(".git")
    url = url.replace("git@github.com:", "").replace("https://github.com/", "")
    return url or None


def detect_test_command() -> str:
    """Best-effort test command for the self-hosted fallback workflow."""
    if Path("Makefile").exists():
        txt = Path("Makefile").read_text()
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
        from mcli.workflow.ci.workflow_transform import workflow_has_hosted_job, MARKER, _yaml
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
