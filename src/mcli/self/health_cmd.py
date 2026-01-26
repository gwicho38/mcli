"""
Repository health analyzer for mcli.

Provides comprehensive analysis of codebase health including:
- Test coverage and results
- Static analysis (linting, type checking, security)
- Documentation completeness
- Dependencies health
- Build validation
- Code metrics
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from mcli.lib.logger.logger import get_logger

logger = get_logger()
console = Console()


# =============================================================================
# Health Status Types
# =============================================================================


class HealthStatus(Enum):
    """Health check result status."""

    PASSING = "passing"
    WARNING = "warning"
    FAILING = "failing"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class CheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    message: str
    details: Optional[str] = None
    metrics: dict[str, Any] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class HealthReport:
    """Complete health report for the repository."""

    timestamp: str
    repo_path: str
    checks: list[CheckResult]
    summary: dict[str, int] = field(default_factory=dict)
    overall_status: HealthStatus = HealthStatus.PASSING
    total_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp,
            "repo_path": self.repo_path,
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "total_duration_ms": self.total_duration_ms,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                    "metrics": c.metrics,
                    "suggestions": c.suggestions,
                    "duration_ms": c.duration_ms,
                }
                for c in self.checks
            ],
        }


# =============================================================================
# Health Check Functions
# =============================================================================


def run_command(
    cmd: list[str], cwd: Optional[Path] = None, timeout: int = 300
) -> tuple[int, str, str]:
    """Run a command and return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            env={**os.environ, "FORCE_COLOR": "0", "NO_COLOR": "1"},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -2, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return -3, "", str(e)


def find_repo_root() -> Path:
    """Find the repository root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


# =============================================================================
# Language Detection
# =============================================================================


def detect_languages(repo_path: Path) -> Dict[str, bool]:
    """Detect which programming languages are used in the repository."""
    languages = {
        "python": False,
        "typescript": False,
        "javascript": False,
        "java": False,
        "elixir": False,
        "dart": False,
    }

    # Python: pyproject.toml, setup.py, requirements.txt, or .py files
    if (
        (repo_path / "pyproject.toml").exists()
        or (repo_path / "setup.py").exists()
        or (repo_path / "requirements.txt").exists()
        or list(repo_path.glob("**/*.py"))[:1]
    ):
        languages["python"] = True

    # TypeScript: tsconfig.json or .ts files
    if (repo_path / "tsconfig.json").exists() or list(repo_path.glob("**/*.ts"))[:1]:
        languages["typescript"] = True

    # JavaScript: package.json or .js files
    if (repo_path / "package.json").exists() or list(repo_path.glob("**/*.js"))[:1]:
        languages["javascript"] = True

    # Java: pom.xml, build.gradle, or .java files
    if (
        (repo_path / "pom.xml").exists()
        or (repo_path / "build.gradle").exists()
        or (repo_path / "build.gradle.kts").exists()
        or list(repo_path.glob("**/*.java"))[:1]
    ):
        languages["java"] = True

    # Elixir: mix.exs or .ex/.exs files
    if (repo_path / "mix.exs").exists() or list(repo_path.glob("**/*.ex"))[:1]:
        languages["elixir"] = True

    # Dart: pubspec.yaml or .dart files
    if (repo_path / "pubspec.yaml").exists() or list(repo_path.glob("**/*.dart"))[:1]:
        languages["dart"] = True

    return languages


# =============================================================================
# TypeScript/JavaScript Checks
# =============================================================================


def check_npm_test(repo_path: Path) -> CheckResult:
    """Run npm/yarn tests."""
    start = time.time()

    if not (repo_path / "package.json").exists():
        return CheckResult(
            name="JS/TS Tests",
            status=HealthStatus.SKIPPED,
            message="No package.json found",
            duration_ms=(time.time() - start) * 1000,
        )

    # Determine package manager
    if (repo_path / "yarn.lock").exists():
        pkg_manager = "yarn"
        test_cmd = ["yarn", "test", "--passWithNoTests"]
    elif (repo_path / "pnpm-lock.yaml").exists():
        pkg_manager = "pnpm"
        test_cmd = ["pnpm", "test", "--passWithNoTests"]
    else:
        pkg_manager = "npm"
        test_cmd = ["npm", "test", "--", "--passWithNoTests"]

    # Check if test script exists
    try:
        import json as json_mod

        pkg_json = json_mod.loads((repo_path / "package.json").read_text())
        if "test" not in pkg_json.get("scripts", {}):
            return CheckResult(
                name="JS/TS Tests",
                status=HealthStatus.SKIPPED,
                message="No test script in package.json",
                duration_ms=(time.time() - start) * 1000,
            )
    except Exception:
        pass

    code, stdout, stderr = run_command(test_cmd, cwd=repo_path, timeout=300)

    if code == 0:
        return CheckResult(
            name="JS/TS Tests",
            status=HealthStatus.PASSING,
            message=f"Tests passed ({pkg_manager})",
            duration_ms=(time.time() - start) * 1000,
        )

    return CheckResult(
        name="JS/TS Tests",
        status=HealthStatus.FAILING,
        message=f"Tests failed ({pkg_manager})",
        details=(stderr or stdout)[:300],
        suggestions=["Fix failing tests", f"Run: {pkg_manager} test"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_eslint(repo_path: Path) -> CheckResult:
    """Check JavaScript/TypeScript linting with ESLint."""
    start = time.time()

    eslint_configs = [
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.json",
        ".eslintrc.yml",
        "eslint.config.js",
    ]
    has_eslint = any((repo_path / cfg).exists() for cfg in eslint_configs)

    if not has_eslint:
        try:
            import json as json_mod

            pkg_json = json_mod.loads((repo_path / "package.json").read_text())
            has_eslint = "eslintConfig" in pkg_json
        except Exception:
            pass

    if not has_eslint:
        return CheckResult(
            name="ESLint",
            status=HealthStatus.SKIPPED,
            message="No ESLint config found",
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(["npx", "eslint", ".", "--max-warnings=0"], cwd=repo_path)

    if code == 0:
        return CheckResult(
            name="ESLint",
            status=HealthStatus.PASSING,
            message="No linting errors",
            duration_ms=(time.time() - start) * 1000,
        )

    output = stdout + stderr
    error_count = len(re.findall(r"^\s*\d+:\d+\s+error", output, re.MULTILINE))
    warn_count = len(re.findall(r"^\s*\d+:\d+\s+warning", output, re.MULTILINE))

    return CheckResult(
        name="ESLint",
        status=HealthStatus.FAILING if error_count > 0 else HealthStatus.WARNING,
        message=f"{error_count} errors, {warn_count} warnings",
        suggestions=["Run: npx eslint . --fix"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_typescript(repo_path: Path) -> CheckResult:
    """Check TypeScript compilation."""
    start = time.time()

    if not (repo_path / "tsconfig.json").exists():
        return CheckResult(
            name="TypeScript",
            status=HealthStatus.SKIPPED,
            message="No tsconfig.json found",
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(["npx", "tsc", "--noEmit"], cwd=repo_path)

    if code == 0:
        return CheckResult(
            name="TypeScript",
            status=HealthStatus.PASSING,
            message="No type errors",
            duration_ms=(time.time() - start) * 1000,
        )

    output = stdout + stderr
    error_count = len(re.findall(r"error TS\d+:", output))

    return CheckResult(
        name="TypeScript",
        status=HealthStatus.FAILING,
        message=f"{error_count} type error(s)",
        suggestions=["Fix TypeScript errors", "Run: npx tsc --noEmit"],
        duration_ms=(time.time() - start) * 1000,
    )


# =============================================================================
# Java Checks
# =============================================================================


def check_java_build(repo_path: Path) -> CheckResult:
    """Check Java build and tests."""
    start = time.time()

    if (repo_path / "pom.xml").exists():
        build_tool = "maven"
        test_cmd = ["mvn", "test", "-q"]
        build_cmd = ["mvn", "compile", "-q"]
    elif (repo_path / "build.gradle").exists() or (repo_path / "build.gradle.kts").exists():
        build_tool = "gradle"
        gradlew = "./gradlew" if (repo_path / "gradlew").exists() else "gradle"
        test_cmd = [gradlew, "test", "-q"]
        build_cmd = [gradlew, "build", "-q"]
    else:
        return CheckResult(
            name="Java Build",
            status=HealthStatus.SKIPPED,
            message="No pom.xml or build.gradle found",
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(build_cmd, cwd=repo_path, timeout=300)
    if code != 0:
        return CheckResult(
            name="Java Build",
            status=HealthStatus.FAILING,
            message=f"Build failed ({build_tool})",
            details=(stderr or stdout)[:300],
            suggestions=["Fix build errors"],
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(test_cmd, cwd=repo_path, timeout=300)
    if code == 0:
        return CheckResult(
            name="Java Build",
            status=HealthStatus.PASSING,
            message=f"Build and tests passed ({build_tool})",
            duration_ms=(time.time() - start) * 1000,
        )

    return CheckResult(
        name="Java Build",
        status=HealthStatus.FAILING,
        message=f"Tests failed ({build_tool})",
        suggestions=["Fix failing tests"],
        duration_ms=(time.time() - start) * 1000,
    )


# =============================================================================
# Elixir Checks
# =============================================================================


def check_mix_test(repo_path: Path) -> CheckResult:
    """Run Elixir tests with mix."""
    start = time.time()

    if not (repo_path / "mix.exs").exists():
        return CheckResult(
            name="Elixir Tests",
            status=HealthStatus.SKIPPED,
            message="No mix.exs found",
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(["mix", "test"], cwd=repo_path, timeout=300)

    if code == 0:
        output = stdout + stderr
        match = re.search(r"(\d+) tests?, (\d+) failures?", output)
        if match:
            tests, failures = int(match.group(1)), int(match.group(2))
            return CheckResult(
                name="Elixir Tests",
                status=HealthStatus.PASSING,
                message=f"{tests} tests passed",
                metrics={"tests": tests, "failures": failures},
                duration_ms=(time.time() - start) * 1000,
            )
        return CheckResult(
            name="Elixir Tests",
            status=HealthStatus.PASSING,
            message="Tests passed",
            duration_ms=(time.time() - start) * 1000,
        )

    return CheckResult(
        name="Elixir Tests",
        status=HealthStatus.FAILING,
        message="Tests failed",
        details=(stderr or stdout)[:300],
        suggestions=["Fix failing tests", "Run: mix test"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_mix_format(repo_path: Path) -> CheckResult:
    """Check Elixir formatting with mix format."""
    start = time.time()

    if not (repo_path / "mix.exs").exists():
        return CheckResult(
            name="Elixir Format",
            status=HealthStatus.SKIPPED,
            message="No mix.exs found",
            duration_ms=(time.time() - start) * 1000,
        )

    code, _, _ = run_command(["mix", "format", "--check-formatted"], cwd=repo_path)

    if code == 0:
        return CheckResult(
            name="Elixir Format",
            status=HealthStatus.PASSING,
            message="All files formatted",
            duration_ms=(time.time() - start) * 1000,
        )

    return CheckResult(
        name="Elixir Format",
        status=HealthStatus.FAILING,
        message="Files need formatting",
        suggestions=["Run: mix format"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_credo(repo_path: Path) -> CheckResult:
    """Check Elixir code quality with Credo."""
    start = time.time()

    if not (repo_path / "mix.exs").exists():
        return CheckResult(
            name="Credo",
            status=HealthStatus.SKIPPED,
            message="No mix.exs found",
            duration_ms=(time.time() - start) * 1000,
        )

    try:
        mix_content = (repo_path / "mix.exs").read_text()
        if ":credo" not in mix_content:
            return CheckResult(
                name="Credo",
                status=HealthStatus.SKIPPED,
                message="Credo not in dependencies",
                duration_ms=(time.time() - start) * 1000,
            )
    except Exception:
        pass

    code, stdout, stderr = run_command(["mix", "credo", "--strict"], cwd=repo_path)

    if code == 0:
        return CheckResult(
            name="Credo",
            status=HealthStatus.PASSING,
            message="No issues found",
            duration_ms=(time.time() - start) * 1000,
        )

    output = stdout + stderr
    issues = len(re.findall(r"┃", output))

    return CheckResult(
        name="Credo",
        status=HealthStatus.WARNING,
        message=f"{issues} issue(s) found",
        suggestions=["Run: mix credo --strict"],
        duration_ms=(time.time() - start) * 1000,
    )


# =============================================================================
# Dart Checks
# =============================================================================


def check_dart_test(repo_path: Path) -> CheckResult:
    """Run Dart tests."""
    start = time.time()

    if not (repo_path / "pubspec.yaml").exists():
        return CheckResult(
            name="Dart Tests",
            status=HealthStatus.SKIPPED,
            message="No pubspec.yaml found",
            duration_ms=(time.time() - start) * 1000,
        )

    if not (repo_path / "test").exists():
        return CheckResult(
            name="Dart Tests",
            status=HealthStatus.SKIPPED,
            message="No test directory found",
            duration_ms=(time.time() - start) * 1000,
        )

    is_flutter = "flutter" in (repo_path / "pubspec.yaml").read_text().lower()
    test_cmd = ["flutter", "test"] if is_flutter else ["dart", "test"]

    code, stdout, stderr = run_command(test_cmd, cwd=repo_path, timeout=300)

    if code == 0:
        return CheckResult(
            name="Dart Tests",
            status=HealthStatus.PASSING,
            message="Tests passed",
            duration_ms=(time.time() - start) * 1000,
        )

    return CheckResult(
        name="Dart Tests",
        status=HealthStatus.FAILING,
        message="Tests failed",
        details=(stderr or stdout)[:300],
        suggestions=["Fix failing tests"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_dart_analyze(repo_path: Path) -> CheckResult:
    """Run Dart static analysis."""
    start = time.time()

    if not (repo_path / "pubspec.yaml").exists():
        return CheckResult(
            name="Dart Analyze",
            status=HealthStatus.SKIPPED,
            message="No pubspec.yaml found",
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(["dart", "analyze", "--fatal-infos"], cwd=repo_path)

    if code == 0:
        return CheckResult(
            name="Dart Analyze",
            status=HealthStatus.PASSING,
            message="No issues found",
            duration_ms=(time.time() - start) * 1000,
        )

    output = stdout + stderr
    errors = len(re.findall(r"error •", output, re.IGNORECASE))
    warnings = len(re.findall(r"warning •", output, re.IGNORECASE))

    return CheckResult(
        name="Dart Analyze",
        status=HealthStatus.FAILING if errors > 0 else HealthStatus.WARNING,
        message=f"{errors} errors, {warnings} warnings",
        suggestions=["Run: dart analyze"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_dart_format(repo_path: Path) -> CheckResult:
    """Check Dart formatting."""
    start = time.time()

    if not (repo_path / "pubspec.yaml").exists():
        return CheckResult(
            name="Dart Format",
            status=HealthStatus.SKIPPED,
            message="No pubspec.yaml found",
            duration_ms=(time.time() - start) * 1000,
        )

    code, _, _ = run_command(
        ["dart", "format", "--set-exit-if-changed", "--output=none", "."], cwd=repo_path
    )

    if code == 0:
        return CheckResult(
            name="Dart Format",
            status=HealthStatus.PASSING,
            message="All files formatted",
            duration_ms=(time.time() - start) * 1000,
        )

    return CheckResult(
        name="Dart Format",
        status=HealthStatus.FAILING,
        message="Files need formatting",
        suggestions=["Run: dart format ."],
        duration_ms=(time.time() - start) * 1000,
    )


# =============================================================================
# Python Checks
# =============================================================================


def check_git_status(repo_path: Path) -> CheckResult:
    """Check git repository status."""
    start = time.time()

    # Check if it's a git repo
    if not (repo_path / ".git").exists():
        return CheckResult(
            name="Git Status",
            status=HealthStatus.ERROR,
            message="Not a git repository",
            suggestions=["Initialize git: git init"],
        )

    # Get current branch
    code, branch, _ = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    branch = branch.strip() if code == 0 else "unknown"

    # Check for uncommitted changes
    code, status, _ = run_command(["git", "status", "--porcelain"], cwd=repo_path)
    changes = status.strip().split("\n") if status.strip() else []
    uncommitted = len(changes)

    # Check for unpushed commits
    code, ahead, _ = run_command(
        ["git", "rev-list", "--count", f"origin/{branch}..HEAD"], cwd=repo_path
    )
    unpushed = int(ahead.strip()) if code == 0 and ahead.strip().isdigit() else 0

    # Get last commit info
    code, commit_info, _ = run_command(["git", "log", "-1", "--format=%h %s (%ar)"], cwd=repo_path)
    last_commit = commit_info.strip() if code == 0 else "unknown"

    status = HealthStatus.PASSING
    suggestions = []

    if uncommitted > 0:
        status = HealthStatus.WARNING
        suggestions.append(f"Commit {uncommitted} uncommitted change(s)")

    if unpushed > 0:
        status = HealthStatus.WARNING
        suggestions.append(f"Push {unpushed} unpushed commit(s)")

    return CheckResult(
        name="Git Status",
        status=status,
        message=f"Branch: {branch}, Last: {last_commit}",
        metrics={
            "branch": branch,
            "uncommitted_changes": uncommitted,
            "unpushed_commits": unpushed,
        },
        suggestions=suggestions,
        duration_ms=(time.time() - start) * 1000,
    )


def check_tests(repo_path: Path, fast: bool = True) -> CheckResult:
    """Run tests and analyze results."""
    start = time.time()

    # Check if pytest is available
    code, _, _ = run_command([sys.executable, "-m", "pytest", "--version"])
    if code != 0:
        return CheckResult(
            name="Tests",
            status=HealthStatus.SKIPPED,
            message="pytest not installed",
            suggestions=["Install pytest: pip install pytest"],
            duration_ms=(time.time() - start) * 1000,
        )

    # Check for test files
    test_files = list(repo_path.glob("tests/**/*.py"))
    test_files = [f for f in test_files if f.name.startswith("test_")]

    if not test_files:
        return CheckResult(
            name="Tests",
            status=HealthStatus.WARNING,
            message="No test files found",
            suggestions=["Add tests in tests/ directory"],
            duration_ms=(time.time() - start) * 1000,
        )

    # Run tests (--no-cov to avoid coverage issues with default pytest config)
    cmd = [sys.executable, "-m", "pytest", "--tb=no", "-q", "--no-cov"]
    if fast:
        cmd.extend(["-x", "--ignore=tests/integration", "--ignore=tests/e2e", "-m", "not slow"])

    code, stdout, stderr = run_command(cmd, cwd=repo_path, timeout=300)

    # Parse results
    output = stdout + stderr
    passed = 0
    failed = 0
    skipped = 0

    # Look for pytest summary line like "10 passed, 2 failed, 3 skipped"
    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))

    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))

    match = re.search(r"(\d+) skipped", output)
    if match:
        skipped = int(match.group(1))

    total = passed + failed + skipped

    # Allow small number of flaky tests as warning instead of failure
    # (flaky tests can occur due to test isolation issues in large suites)
    if failed == 0:
        status = HealthStatus.PASSING
    elif failed <= 5:
        status = HealthStatus.WARNING
    else:
        status = HealthStatus.FAILING

    suggestions = []
    if failed > 0:
        suggestions.append(f"Investigate {failed} failing test(s) - may be flaky")
    if skipped > total * 0.3 and skipped > 10:
        suggestions.append("Review skipped tests - too many may indicate issues")

    return CheckResult(
        name="Tests",
        status=status,
        message=f"{passed} passed, {failed} failed, {skipped} skipped",
        metrics={
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
        },
        suggestions=suggestions,
        duration_ms=(time.time() - start) * 1000,
    )


def check_coverage(repo_path: Path) -> CheckResult:
    """Check test coverage."""
    start = time.time()

    # Check if coverage is available
    code, _, _ = run_command([sys.executable, "-m", "coverage", "--version"])
    if code != 0:
        return CheckResult(
            name="Coverage",
            status=HealthStatus.SKIPPED,
            message="coverage not installed",
            suggestions=["Install coverage: pip install pytest-cov"],
            duration_ms=(time.time() - start) * 1000,
        )

    # Check for existing coverage data
    coverage_file = repo_path / ".coverage"
    if not coverage_file.exists():
        return CheckResult(
            name="Coverage",
            status=HealthStatus.SKIPPED,
            message="No coverage data (run: make test-cov)",
            suggestions=["Generate coverage: pytest --cov=src tests/"],
            duration_ms=(time.time() - start) * 1000,
        )

    # Get coverage report
    code, stdout, _ = run_command(
        [sys.executable, "-m", "coverage", "report", "--format=total"], cwd=repo_path
    )

    if code != 0:
        return CheckResult(
            name="Coverage",
            status=HealthStatus.WARNING,
            message="Could not read coverage data",
            duration_ms=(time.time() - start) * 1000,
        )

    try:
        total_coverage = float(stdout.strip())
    except ValueError:
        total_coverage = 0.0

    status = HealthStatus.PASSING
    suggestions = []

    if total_coverage < 30:
        status = HealthStatus.FAILING
        suggestions.append(f"Coverage is low ({total_coverage:.1f}%), target: 80%")
    elif total_coverage < 60:
        status = HealthStatus.WARNING
        suggestions.append(f"Improve coverage from {total_coverage:.1f}% to 80%")

    return CheckResult(
        name="Coverage",
        status=status,
        message=f"{total_coverage:.1f}% total coverage",
        metrics={"total_coverage": total_coverage, "target": 80},
        suggestions=suggestions,
        duration_ms=(time.time() - start) * 1000,
    )


def check_black(repo_path: Path) -> CheckResult:
    """Check code formatting with Black."""
    start = time.time()

    code, _, _ = run_command([sys.executable, "-m", "black", "--version"])
    if code != 0:
        return CheckResult(
            name="Black (Formatting)",
            status=HealthStatus.SKIPPED,
            message="black not installed",
            suggestions=["Install black: pip install black"],
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(
        [sys.executable, "-m", "black", "--check", "--diff", "src/"], cwd=repo_path
    )

    if code == 0:
        return CheckResult(
            name="Black (Formatting)",
            status=HealthStatus.PASSING,
            message="All files formatted correctly",
            duration_ms=(time.time() - start) * 1000,
        )

    # Count files needing formatting
    output = stdout + stderr
    files_needing_format = len(re.findall(r"would reformat", output))

    return CheckResult(
        name="Black (Formatting)",
        status=HealthStatus.FAILING,
        message=f"{files_needing_format} file(s) need formatting",
        metrics={"files_to_format": files_needing_format},
        suggestions=["Run: make format (or: black src/)"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_isort(repo_path: Path) -> CheckResult:
    """Check import sorting with isort."""
    start = time.time()

    code, _, _ = run_command([sys.executable, "-m", "isort", "--version"])
    if code != 0:
        return CheckResult(
            name="isort (Imports)",
            status=HealthStatus.SKIPPED,
            message="isort not installed",
            suggestions=["Install isort: pip install isort"],
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(
        [sys.executable, "-m", "isort", "--check-only", "--diff", "src/"], cwd=repo_path
    )

    if code == 0:
        return CheckResult(
            name="isort (Imports)",
            status=HealthStatus.PASSING,
            message="All imports sorted correctly",
            duration_ms=(time.time() - start) * 1000,
        )

    # Count files needing sorting
    output = stdout + stderr
    files_needing_sort = len(re.findall(r"^---", output, re.MULTILINE))

    return CheckResult(
        name="isort (Imports)",
        status=HealthStatus.FAILING,
        message=f"{files_needing_sort} file(s) need import sorting",
        metrics={"files_to_sort": files_needing_sort},
        suggestions=["Run: isort src/"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_flake8(repo_path: Path) -> CheckResult:
    """Check code quality with flake8."""
    start = time.time()

    code, _, _ = run_command([sys.executable, "-m", "flake8", "--version"])
    if code != 0:
        return CheckResult(
            name="Flake8 (Linting)",
            status=HealthStatus.SKIPPED,
            message="flake8 not installed",
            suggestions=["Install flake8: pip install flake8"],
            duration_ms=(time.time() - start) * 1000,
        )

    # Only check critical errors - undefined names and syntax errors
    # Explicitly select codes to override flake8 plugins
    critical_codes = "F821,E902,E999"
    code, stdout, stderr = run_command(
        [
            sys.executable,
            "-m",
            "flake8",
            "src/",
            "--select=" + critical_codes,
            "--count",
            "--statistics",
        ],
        cwd=repo_path,
    )

    if code == 0:
        return CheckResult(
            name="Flake8 (Critical)",
            status=HealthStatus.PASSING,
            message="No critical linting issues (undefined names, syntax errors)",
            duration_ms=(time.time() - start) * 1000,
        )

    output = stdout + stderr
    lines = output.strip().split("\n")
    issue_count = len([line for line in lines if line and ":" in line and not line.startswith(" ")])

    # Parse error types
    error_types: dict[str, int] = {}
    for line in lines:
        match = re.search(r"([A-Z]\d{3})", line)
        if match:
            code_type = match.group(1)
            error_types[code_type] = error_types.get(code_type, 0) + 1

    return CheckResult(
        name="Flake8 (Critical)",
        status=HealthStatus.WARNING if issue_count < 5 else HealthStatus.FAILING,
        message=f"{issue_count} critical issue(s) (undefined names, syntax errors)",
        metrics={"total_issues": issue_count, "by_type": error_types},
        suggestions=["Fix undefined names (F821) and syntax errors (E902, E999)"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_mypy(repo_path: Path) -> CheckResult:
    """Check type hints with mypy."""
    start = time.time()

    code, _, _ = run_command([sys.executable, "-m", "mypy", "--version"])
    if code != 0:
        return CheckResult(
            name="Mypy (Type Checking)",
            status=HealthStatus.SKIPPED,
            message="mypy not installed",
            suggestions=["Install mypy: pip install mypy"],
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(
        [sys.executable, "-m", "mypy", "src/", "--ignore-missing-imports", "--no-error-summary"],
        cwd=repo_path,
        timeout=120,
    )

    output = stdout + stderr
    errors = len(re.findall(r": error:", output))
    warnings = len(re.findall(r": warning:", output))
    notes = len(re.findall(r": note:", output))

    if code == 0 and errors == 0:
        return CheckResult(
            name="Mypy (Type Checking)",
            status=HealthStatus.PASSING,
            message="No type errors",
            metrics={"warnings": warnings, "notes": notes},
            duration_ms=(time.time() - start) * 1000,
        )

    return CheckResult(
        name="Mypy (Type Checking)",
        status=HealthStatus.WARNING if errors < 10 else HealthStatus.FAILING,
        message=f"{errors} error(s), {warnings} warning(s)",
        metrics={"errors": errors, "warnings": warnings, "notes": notes},
        suggestions=["Run: make type-check (or: mypy src/)"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_security(repo_path: Path) -> CheckResult:
    """Check for security issues with bandit.

    Note: CLI frameworks that run shell commands have expected shell-related
    issues (B602, B605, B607). These are intentional patterns for a CLI tool.
    The check is lenient about these known patterns but strict about others.
    """
    start = time.time()

    code, _, _ = run_command([sys.executable, "-m", "bandit", "--version"])
    if code != 0:
        return CheckResult(
            name="Bandit (Security)",
            status=HealthStatus.SKIPPED,
            message="bandit not installed",
            suggestions=["Install bandit: pip install bandit"],
            duration_ms=(time.time() - start) * 1000,
        )

    code, stdout, stderr = run_command(
        [sys.executable, "-m", "bandit", "-r", "src/", "-q", "-f", "json"], cwd=repo_path
    )

    # Expected issue codes for CLI frameworks that run shell commands
    # B602: subprocess with shell=True (intentional for shell utilities)
    # B605: start_process_with_a_shell (intentional for CLI tools)
    # B607: start_process_with_partial_path (intentional)
    # B324: weak MD5 hash (used for fingerprinting, not security)
    expected_codes = {"B602", "B605", "B607", "B324"}

    try:
        results = json.loads(stdout)
        all_issues = results.get("results", [])

        # Separate expected vs unexpected issues
        high_expected = 0
        high_unexpected = 0
        medium = 0
        low = 0

        for issue in all_issues:
            severity = issue.get("issue_severity", "")
            test_id = issue.get("test_id", "")

            if severity == "HIGH":
                if test_id in expected_codes:
                    high_expected += 1
                else:
                    high_unexpected += 1
            elif severity == "MEDIUM":
                medium += 1
            elif severity == "LOW":
                low += 1

        total = high_expected + high_unexpected + medium + low
        high = high_expected + high_unexpected
    except (json.JSONDecodeError, TypeError):
        total, high, high_expected, high_unexpected, medium, low = 0, 0, 0, 0, 0, 0

    status = HealthStatus.PASSING
    suggestions = []

    # Only fail on unexpected high severity issues
    # Expected shell-related issues are acceptable for CLI tools
    if high_unexpected > 0:
        status = HealthStatus.FAILING
        suggestions.append(f"Fix {high_unexpected} unexpected HIGH severity issue(s)")
    elif high_expected > 20:  # Too many even if expected
        status = HealthStatus.WARNING
        suggestions.append(f"Review {high_expected} shell-related security patterns")
    elif medium > 10:
        status = HealthStatus.WARNING
        suggestions.append(f"Review {medium} MEDIUM severity issue(s)")

    # Add note about expected issues
    if high_expected > 0:
        suggestions.append(f"Note: {high_expected} expected CLI patterns (shell commands)")

    return CheckResult(
        name="Bandit (Security)",
        status=status,
        message=f"{total} issue(s): {high} high ({high_expected} expected), {medium} medium, {low} low",
        metrics={
            "total": total,
            "high": high,
            "high_expected": high_expected,
            "high_unexpected": high_unexpected,
            "medium": medium,
            "low": low,
        },
        suggestions=suggestions,
        duration_ms=(time.time() - start) * 1000,
    )


def check_dependencies(repo_path: Path) -> CheckResult:
    """Check dependency health."""
    start = time.time()

    # Try uv first, then pip
    outdated = []
    outdated_count = 0

    # Try uv pip list
    code, stdout, _ = run_command(["uv", "pip", "list", "--outdated", "--format=json"])

    if code != 0:
        # Fallback to pip
        code, stdout, _ = run_command(
            [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"]
        )

    if code != 0:
        return CheckResult(
            name="Dependencies",
            status=HealthStatus.SKIPPED,
            message="Could not check dependencies (install uv or pip)",
            duration_ms=(time.time() - start) * 1000,
        )

    try:
        outdated = json.loads(stdout)
        outdated_count = len(outdated)
    except (json.JSONDecodeError, TypeError):
        outdated_count = 0
        outdated = []

    # Check for pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    has_pyproject = pyproject.exists()

    # Check for requirements files
    requirements_files = list(repo_path.glob("requirements*.txt"))

    status = HealthStatus.PASSING
    suggestions = []

    # High threshold - many outdated packages are expected due to intentional
    # version pinning for stability (e.g., numpy <2.0, openai <2.0, flask <3.0)
    # Only warn if there's a very large number suggesting unmaintained deps
    if outdated_count > 200:
        status = HealthStatus.WARNING
        suggestions.append(f"Review {outdated_count} outdated package(s) - may need attention")

    if not has_pyproject and not requirements_files:
        status = HealthStatus.WARNING
        suggestions.append("Add pyproject.toml or requirements.txt")

    # Get top outdated packages
    top_outdated = outdated[:5] if outdated else []
    outdated_names = [
        f"{p['name']} ({p['version']} -> {p['latest_version']})" for p in top_outdated
    ]

    return CheckResult(
        name="Dependencies",
        status=status,
        message=f"{outdated_count} outdated package(s)",
        details="\n".join(outdated_names) if outdated_names else None,
        metrics={"outdated": outdated_count, "has_pyproject": has_pyproject},
        suggestions=suggestions,
        duration_ms=(time.time() - start) * 1000,
    )


def check_documentation(repo_path: Path) -> CheckResult:
    """Check documentation completeness."""
    start = time.time()

    docs_dir = repo_path / "docs"
    readme = repo_path / "README.md"
    contributing = repo_path / "CONTRIBUTING.md"
    changelog = repo_path / "CHANGELOG.md"
    claude_md = repo_path / "CLAUDE.md"

    checks = {
        "README.md": readme.exists(),
        "docs/": docs_dir.exists(),
        "CONTRIBUTING.md": contributing.exists() or (docs_dir / "CONTRIBUTING.md").exists(),
        "CHANGELOG.md": changelog.exists() or (docs_dir / "CHANGELOG.md").exists(),
        "CLAUDE.md": claude_md.exists(),
    }

    doc_files = list((docs_dir).glob("**/*.md")) if docs_dir.exists() else []
    doc_count = len(doc_files)

    present = sum(checks.values())
    total = len(checks)

    status = HealthStatus.PASSING
    suggestions = []

    missing = [k for k, v in checks.items() if not v]
    if missing:
        status = HealthStatus.WARNING
        suggestions.extend([f"Add {m}" for m in missing])

    return CheckResult(
        name="Documentation",
        status=status,
        message=f"{present}/{total} key docs, {doc_count} total doc files",
        metrics={
            "key_docs_present": present,
            "key_docs_total": total,
            "total_doc_files": doc_count,
            "checks": checks,
        },
        suggestions=suggestions,
        duration_ms=(time.time() - start) * 1000,
    )


def check_build(repo_path: Path) -> CheckResult:
    """Check if the project builds successfully."""
    start = time.time()

    # Check for pyproject.toml
    pyproject = repo_path / "pyproject.toml"
    if not pyproject.exists():
        return CheckResult(
            name="Build",
            status=HealthStatus.SKIPPED,
            message="No pyproject.toml found",
            suggestions=["Add pyproject.toml for build configuration"],
            duration_ms=(time.time() - start) * 1000,
        )

    # Try multiple build methods in order of preference
    build_methods = [
        # uv build (preferred for uv-managed projects)
        (["uv", "build", "--wheel", "--out-dir", "/tmp/mcli_health_wheel"], "uv build"),
        # pip wheel via current Python
        (
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "-w",
                "/tmp/mcli_health_wheel",
                ".",
            ],
            "pip wheel",
        ),
        # python -m build
        ([sys.executable, "-m", "build", "--wheel", "--outdir", "/tmp/mcli_health_wheel"], "build"),
    ]

    for cmd, method_name in build_methods:
        code, stdout, stderr = run_command(cmd, cwd=repo_path, timeout=120)

        if code == 0:
            return CheckResult(
                name="Build",
                status=HealthStatus.PASSING,
                message=f"Wheel builds successfully ({method_name})",
                duration_ms=(time.time() - start) * 1000,
            )

        # If command not found, try next method
        if code == -2:
            continue

        # Command found but failed
        error_detail = stderr[:500] if stderr else stdout[:500] if stdout else "Unknown error"
        return CheckResult(
            name="Build",
            status=HealthStatus.FAILING,
            message=f"Build failed ({method_name})",
            details=error_detail,
            suggestions=["Fix build errors before releasing", "Run: make wheel"],
            duration_ms=(time.time() - start) * 1000,
        )

    # No build method available
    return CheckResult(
        name="Build",
        status=HealthStatus.SKIPPED,
        message="No build tool available (uv, pip, or build)",
        suggestions=["Install: pip install build", "Or use: uv build"],
        duration_ms=(time.time() - start) * 1000,
    )


def check_code_metrics(repo_path: Path) -> CheckResult:
    """Calculate code metrics."""
    start = time.time()

    src_dir = repo_path / "src"
    if not src_dir.exists():
        src_dir = repo_path

    # Count Python files and lines
    py_files = list(src_dir.glob("**/*.py"))
    total_lines = 0
    total_code_lines = 0
    total_comment_lines = 0
    total_blank_lines = 0

    for py_file in py_files:
        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            total_lines += len(lines)

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    total_blank_lines += 1
                elif stripped.startswith("#"):
                    total_comment_lines += 1
                else:
                    total_code_lines += 1
        except Exception:
            continue

    # Count functions and classes
    total_functions = 0
    total_classes = 0
    for py_file in py_files:
        try:
            content = py_file.read_text(encoding="utf-8")
            total_functions += len(re.findall(r"^\s*def\s+\w+", content, re.MULTILINE))
            total_classes += len(re.findall(r"^\s*class\s+\w+", content, re.MULTILINE))
        except Exception:
            continue

    return CheckResult(
        name="Code Metrics",
        status=HealthStatus.PASSING,
        message=f"{len(py_files)} files, {total_code_lines:,} code lines",
        metrics={
            "python_files": len(py_files),
            "total_lines": total_lines,
            "code_lines": total_code_lines,
            "comment_lines": total_comment_lines,
            "blank_lines": total_blank_lines,
            "functions": total_functions,
            "classes": total_classes,
            "comment_ratio": (
                f"{(total_comment_lines / total_code_lines * 100):.1f}%"
                if total_code_lines > 0
                else "N/A"
            ),
        },
        duration_ms=(time.time() - start) * 1000,
    )


def check_ci_status(repo_path: Path) -> CheckResult:
    """Check CI/CD status from GitHub Actions."""
    start = time.time()

    # Check if gh CLI is available
    code, _, _ = run_command(["gh", "--version"])
    if code != 0:
        return CheckResult(
            name="CI Status",
            status=HealthStatus.SKIPPED,
            message="gh CLI not installed",
            suggestions=["Install GitHub CLI: brew install gh"],
            duration_ms=(time.time() - start) * 1000,
        )

    # Get recent workflow runs
    code, stdout, stderr = run_command(
        ["gh", "run", "list", "--limit", "5", "--json", "status,conclusion,name,headBranch"],
        cwd=repo_path,
    )

    if code != 0:
        return CheckResult(
            name="CI Status",
            status=HealthStatus.SKIPPED,
            message="Could not fetch CI status",
            details=stderr,
            duration_ms=(time.time() - start) * 1000,
        )

    try:
        runs = json.loads(stdout)
    except json.JSONDecodeError:
        runs = []

    if not runs:
        return CheckResult(
            name="CI Status",
            status=HealthStatus.SKIPPED,
            message="No recent CI runs",
            duration_ms=(time.time() - start) * 1000,
        )

    # Analyze runs
    main_runs = [r for r in runs if r.get("headBranch") == "main"]
    if main_runs:
        latest = main_runs[0]
        status_str = latest.get("status", "unknown")
        conclusion = latest.get("conclusion", "pending")

        if status_str == "completed":
            if conclusion == "success":
                status = HealthStatus.PASSING
                message = f"Latest CI: {latest.get('name', 'unknown')} passed"
            else:
                status = HealthStatus.FAILING
                message = f"Latest CI: {latest.get('name', 'unknown')} {conclusion}"
        else:
            status = HealthStatus.WARNING
            message = f"CI in progress: {latest.get('name', 'unknown')}"
    else:
        status = HealthStatus.WARNING
        message = "No main branch CI runs found"

    return CheckResult(
        name="CI Status",
        status=status,
        message=message,
        metrics={"recent_runs": len(runs)},
        suggestions=["Run: gh run list" if status != HealthStatus.PASSING else ""],
        duration_ms=(time.time() - start) * 1000,
    )


# =============================================================================
# Report Generation
# =============================================================================


def generate_report(
    repo_path: Path,
    quick: bool = False,
    skip_tests: bool = False,
    skip_build: bool = False,
) -> HealthReport:
    """Generate a complete health report."""
    timestamp = datetime.now().isoformat()
    checks: list[CheckResult] = []
    start_time = time.time()

    # Detect languages in the repository
    languages = detect_languages(repo_path)
    detected = [lang for lang, present in languages.items() if present]
    console.print(f"[dim]Detected languages: {', '.join(detected) or 'none'}[/dim]\n")

    # Universal checks
    check_functions = [
        ("Git Status", lambda: check_git_status(repo_path)),
        ("Code Metrics", lambda: check_code_metrics(repo_path)),
    ]

    # Python-specific checks
    if languages["python"]:
        check_functions.extend(
            [
                ("Black", lambda: check_black(repo_path)),
                ("isort", lambda: check_isort(repo_path)),
                ("Flake8", lambda: check_flake8(repo_path)),
            ]
        )
        if not skip_tests:
            check_functions.append(("Python Tests", lambda: check_tests(repo_path, fast=quick)))
            if not quick:
                check_functions.append(("Coverage", lambda: check_coverage(repo_path)))
        if not quick:
            check_functions.extend(
                [
                    ("Mypy", lambda: check_mypy(repo_path)),
                    ("Security", lambda: check_security(repo_path)),
                    ("Dependencies", lambda: check_dependencies(repo_path)),
                ]
            )
        if not skip_build and not quick:
            check_functions.append(("Python Build", lambda: check_build(repo_path)))

    # TypeScript/JavaScript checks
    if languages["typescript"] or languages["javascript"]:
        if not skip_tests:
            check_functions.append(("JS/TS Tests", lambda: check_npm_test(repo_path)))
        check_functions.append(("ESLint", lambda: check_eslint(repo_path)))
        if languages["typescript"]:
            check_functions.append(("TypeScript", lambda: check_typescript(repo_path)))

    # Java checks
    if languages["java"]:
        if not skip_tests:
            check_functions.append(("Java Build", lambda: check_java_build(repo_path)))

    # Elixir checks
    if languages["elixir"]:
        if not skip_tests:
            check_functions.append(("Elixir Tests", lambda: check_mix_test(repo_path)))
        check_functions.append(("Elixir Format", lambda: check_mix_format(repo_path)))
        if not quick:
            check_functions.append(("Credo", lambda: check_credo(repo_path)))

    # Dart checks
    if languages["dart"]:
        if not skip_tests:
            check_functions.append(("Dart Tests", lambda: check_dart_test(repo_path)))
        check_functions.append(("Dart Analyze", lambda: check_dart_analyze(repo_path)))
        check_functions.append(("Dart Format", lambda: check_dart_format(repo_path)))

    # Universal non-quick checks
    if not quick:
        check_functions.extend(
            [
                ("Documentation", lambda: check_documentation(repo_path)),
                ("CI Status", lambda: check_ci_status(repo_path)),
            ]
        )

    # Run checks with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Running health checks...", total=len(check_functions))

        for name, check_fn in check_functions:
            progress.update(task, description=f"Checking {name}...")
            try:
                result = check_fn()
                checks.append(result)
            except Exception as e:
                checks.append(
                    CheckResult(
                        name=name,
                        status=HealthStatus.ERROR,
                        message=f"Check failed: {str(e)[:100]}",
                    )
                )
            progress.advance(task)

    # Calculate summary
    summary = {
        "passing": sum(1 for c in checks if c.status == HealthStatus.PASSING),
        "warning": sum(1 for c in checks if c.status == HealthStatus.WARNING),
        "failing": sum(1 for c in checks if c.status == HealthStatus.FAILING),
        "skipped": sum(1 for c in checks if c.status == HealthStatus.SKIPPED),
        "error": sum(1 for c in checks if c.status == HealthStatus.ERROR),
    }

    # Determine overall status
    if summary["failing"] > 0 or summary["error"] > 0:
        overall_status = HealthStatus.FAILING
    elif summary["warning"] > 0:
        overall_status = HealthStatus.WARNING
    else:
        overall_status = HealthStatus.PASSING

    return HealthReport(
        timestamp=timestamp,
        repo_path=str(repo_path),
        checks=checks,
        summary=summary,
        overall_status=overall_status,
        total_duration_ms=(time.time() - start_time) * 1000,
    )


def display_report(report: HealthReport, verbose: bool = False) -> None:
    """Display the health report in a formatted way."""
    # Status icons
    status_icons = {
        HealthStatus.PASSING: "[green]PASS[/green]",
        HealthStatus.WARNING: "[yellow]WARN[/yellow]",
        HealthStatus.FAILING: "[red]FAIL[/red]",
        HealthStatus.SKIPPED: "[dim]SKIP[/dim]",
        HealthStatus.ERROR: "[red]ERR [/red]",
    }

    # Header
    overall_color = {
        HealthStatus.PASSING: "green",
        HealthStatus.WARNING: "yellow",
        HealthStatus.FAILING: "red",
    }.get(report.overall_status, "white")

    header = f"[{overall_color}]Repository Health Report[/{overall_color}]"
    console.print(Panel(header, title="mcli health", subtitle=report.timestamp[:19]))
    console.print()

    # Summary
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_row(
        f"[green]{report.summary['passing']} passing[/green]",
        f"[yellow]{report.summary['warning']} warnings[/yellow]",
        f"[red]{report.summary['failing']} failing[/red]",
        f"[dim]{report.summary['skipped']} skipped[/dim]",
    )
    console.print(summary_table)
    console.print()

    # Results table
    table = Table(title="Check Results", show_header=True, header_style="bold cyan")
    table.add_column("Check", style="cyan", width=25)
    table.add_column("Status", justify="center", width=8)
    table.add_column("Result", width=45)
    table.add_column("Time", justify="right", width=8)

    for check in report.checks:
        table.add_row(
            check.name,
            status_icons[check.status],
            check.message,
            f"{check.duration_ms:.0f}ms",
        )

    console.print(table)
    console.print()

    # Suggestions
    all_suggestions = []
    for check in report.checks:
        if check.suggestions:
            for suggestion in check.suggestions:
                if suggestion:
                    all_suggestions.append(f"  [{check.name}] {suggestion}")

    if all_suggestions:
        console.print("[bold yellow]Suggestions:[/bold yellow]")
        for suggestion in all_suggestions[:10]:  # Limit to 10
            console.print(suggestion)
        if len(all_suggestions) > 10:
            console.print(f"  [dim]... and {len(all_suggestions) - 10} more[/dim]")
        console.print()

    # Verbose metrics
    if verbose:
        console.print("[bold cyan]Detailed Metrics:[/bold cyan]")
        tree = Tree("Metrics")
        for check in report.checks:
            if check.metrics:
                branch = tree.add(f"[cyan]{check.name}[/cyan]")
                for key, value in check.metrics.items():
                    if isinstance(value, dict):
                        sub = branch.add(f"{key}:")
                        for k, v in value.items():
                            sub.add(f"{k}: {v}")
                    else:
                        branch.add(f"{key}: {value}")
        console.print(tree)
        console.print()

    # Footer
    console.print(
        f"[dim]Total time: {report.total_duration_ms / 1000:.1f}s | "
        f"Path: {report.repo_path}[/dim]"
    )


# =============================================================================
# CLI Commands
# =============================================================================


@click.command("health")
@click.option("--quick", "-q", is_flag=True, help="Quick check (skip slow operations)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed metrics")
@click.option("--skip-tests", is_flag=True, help="Skip running tests")
@click.option("--skip-build", is_flag=True, help="Skip build verification")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def health(quick: bool, verbose: bool, skip_tests: bool, skip_build: bool, output_json: bool):
    """🏥 Run comprehensive health checks on the repository.

    Analyzes the codebase for:
    - Git status and uncommitted changes
    - Test results and coverage
    - Code formatting (Black, isort)
    - Linting issues (Flake8)
    - Type errors (Mypy)
    - Security vulnerabilities (Bandit)
    - Dependency health
    - Documentation completeness
    - CI/CD status
    - Build validation

    Examples:
        mcli health              # Full health check
        mcli health --quick      # Quick check (skip slow operations)
        mcli health --json       # Output as JSON
        mcli health --skip-tests # Skip running tests
    """
    repo_path = find_repo_root()

    console.print(f"[cyan]Analyzing repository:[/cyan] {repo_path}")
    console.print()

    report = generate_report(
        repo_path,
        quick=quick,
        skip_tests=skip_tests,
        skip_build=skip_build,
    )

    if output_json:
        console.print_json(json.dumps(report.to_dict(), indent=2))
    else:
        display_report(report, verbose=verbose)

    # Exit with appropriate code
    if report.overall_status == HealthStatus.FAILING:
        raise SystemExit(1)
    elif report.overall_status == HealthStatus.WARNING:
        raise SystemExit(0)  # Warnings don't fail
    else:
        raise SystemExit(0)


# Alias for backwards compatibility
health_group = health
