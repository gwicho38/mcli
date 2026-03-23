"""
Automated release note generation from git history.

Parses conventional commits between tags/refs and generates categorized
markdown release notes.
"""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from mcli.lib.logger.logger import get_logger
from mcli.lib.ui.styling import console, success

logger = get_logger(__name__)

# Conventional commit pattern: type(scope): description
COMMIT_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|test|refactor|perf|ci|build|chore|style|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s*(?P<description>.+)$"
)

CATEGORY_MAP = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "test": "Tests",
    "refactor": "Refactoring",
    "perf": "Performance",
    "ci": "CI/CD",
    "build": "Build",
    "chore": "Chores",
    "style": "Style",
    "revert": "Reverts",
}

CATEGORY_ORDER = [
    "Features",
    "Bug Fixes",
    "Performance",
    "Refactoring",
    "Documentation",
    "Tests",
    "CI/CD",
    "Build",
    "Chores",
    "Style",
    "Reverts",
]


@dataclass
class ParsedCommit:
    """A parsed conventional commit."""

    hash: str
    type: str
    scope: Optional[str]
    description: str
    breaking: bool = False
    pr_number: Optional[str] = None


@dataclass
class ReleaseNotes:
    """Generated release notes."""

    version: str
    date: str
    categories: dict = field(default_factory=dict)
    breaking_changes: list = field(default_factory=list)
    uncategorized: list = field(default_factory=list)

    @property
    def total_commits(self) -> int:
        total = sum(len(commits) for commits in self.categories.values())
        return total + len(self.uncategorized)


def _run_git(args: list[str]) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(["git"] + args, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _get_latest_tag() -> Optional[str]:
    """Get the most recent git tag."""
    try:
        return _run_git(["describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        return None


def _get_commits_between(from_ref: Optional[str], to_ref: str = "HEAD") -> list[str]:
    """Get commit lines between two refs."""
    if from_ref:
        range_spec = f"{from_ref}..{to_ref}"
    else:
        range_spec = to_ref

    output = _run_git(["log", range_spec, "--pretty=format:%H|%s"])
    if not output:
        return []
    return output.splitlines()


def _extract_pr_number(description: str) -> tuple[str, Optional[str]]:
    """Extract PR number from commit description if present."""
    pr_match = re.search(r"\(#(\d+)\)\s*$", description)
    if pr_match:
        pr_num = pr_match.group(1)
        clean_desc = description[: pr_match.start()].strip()
        return clean_desc, pr_num
    return description, None


def parse_commits(raw_lines: list[str]) -> list[ParsedCommit]:
    """Parse raw git log lines into structured commits."""
    commits = []
    for line in raw_lines:
        if "|" not in line:
            continue
        hash_val, subject = line.split("|", 1)
        match = COMMIT_PATTERN.match(subject.strip())
        if match:
            desc, pr_num = _extract_pr_number(match.group("description"))
            commits.append(
                ParsedCommit(
                    hash=hash_val[:8],
                    type=match.group("type"),
                    scope=match.group("scope"),
                    description=desc,
                    breaking=bool(match.group("breaking")),
                    pr_number=pr_num,
                )
            )
        else:
            # Non-conventional commit
            desc, pr_num = _extract_pr_number(subject.strip())
            commits.append(
                ParsedCommit(
                    hash=hash_val[:8],
                    type="",
                    scope=None,
                    description=desc,
                    pr_number=pr_num,
                )
            )
    return commits


def generate_release_notes(
    version: str,
    from_ref: Optional[str] = None,
    to_ref: str = "HEAD",
) -> ReleaseNotes:
    """Generate release notes from git history."""
    raw_lines = _get_commits_between(from_ref, to_ref)
    commits = parse_commits(raw_lines)

    notes = ReleaseNotes(
        version=version,
        date=datetime.now().strftime("%Y-%m-%d"),
    )

    for commit in commits:
        if commit.breaking:
            notes.breaking_changes.append(commit)

        category = CATEGORY_MAP.get(commit.type)
        if category:
            notes.categories.setdefault(category, []).append(commit)
        else:
            notes.uncategorized.append(commit)

    return notes


def render_markdown(notes: ReleaseNotes, repo_url: str = "") -> str:
    """Render release notes as markdown."""
    lines = [f"# Release {notes.version}", "", f"**Date:** {notes.date}", ""]

    if notes.breaking_changes:
        lines.append("## Breaking Changes")
        lines.append("")
        for commit in notes.breaking_changes:
            lines.append(f"- **{commit.description}**")
        lines.append("")

    for category in CATEGORY_ORDER:
        commits = notes.categories.get(category, [])
        if not commits:
            continue
        lines.append(f"## {category}")
        lines.append("")
        for commit in commits:
            scope = f"**{commit.scope}:** " if commit.scope else ""
            pr_link = ""
            if commit.pr_number and repo_url:
                pr_link = f" ([#{commit.pr_number}]({repo_url}/pull/{commit.pr_number}))"
            elif commit.pr_number:
                pr_link = f" (#{commit.pr_number})"
            lines.append(f"- {scope}{commit.description}{pr_link}")
        lines.append("")

    if notes.uncategorized:
        lines.append("## Other Changes")
        lines.append("")
        for commit in notes.uncategorized:
            pr_link = ""
            if commit.pr_number:
                pr_link = f" (#{commit.pr_number})"
            lines.append(f"- {commit.description}{pr_link}")
        lines.append("")

    lines.append("---")
    lines.append(f"*{notes.total_commits} commits in this release*")
    lines.append("")

    return "\n".join(lines)


@click.command("release-notes")
@click.option(
    "--version", "-v", "ver", default=None, help="Version string (default: from pyproject.toml)"
)
@click.option("--from", "from_ref", default=None, help="Start ref (default: latest tag)")
@click.option("--to", "to_ref", default="HEAD", help="End ref (default: HEAD)")
@click.option("--output", "-o", "output_path", default=None, help="Write to file (default: stdout)")
@click.option(
    "--repo-url", default="https://github.com/gwicho38/mcli", help="Repository URL for PR links"
)
def release_notes(ver, from_ref, to_ref, output_path, repo_url):
    """Generate release notes from conventional commits.

    Parses git history between two refs and generates categorized
    markdown release notes.

    Examples:
        mcli self release-notes
        mcli self release-notes --version 8.0.45 --from v8.0.44
        mcli self release-notes -o docs/releases/8.0.45.md
    """
    # Resolve version from pyproject.toml if not provided
    if not ver:
        try:
            import tomli

            pyproject = Path("pyproject.toml")
            if pyproject.exists():
                with open(pyproject, "rb") as f:
                    data = tomli.load(f)
                ver = data.get("project", {}).get("version", "unreleased")
            else:
                ver = "unreleased"
        except Exception:
            ver = "unreleased"

    # Resolve from_ref
    if not from_ref:
        from_ref = _get_latest_tag()
        if from_ref:
            console.print(f"[dim]From tag: {from_ref}[/dim]")

    notes = generate_release_notes(ver, from_ref, to_ref)

    if notes.total_commits == 0:
        console.print("[yellow]No commits found in range.[/yellow]")
        return

    # Show summary table
    table = Table(title=f"Release {ver}", show_header=True)
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green", justify="right")

    for category in CATEGORY_ORDER:
        count = len(notes.categories.get(category, []))
        if count:
            table.add_row(category, str(count))

    if notes.uncategorized:
        table.add_row("Other", str(len(notes.uncategorized)))

    console.print(table)

    # Render markdown
    md = render_markdown(notes, repo_url)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md)
        success(f"Release notes written to {out}")
    else:
        console.print()
        console.print(md)
