"""Unit tests for the health command module."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from mcli.self.health_cmd import (
    CheckResult,
    HealthReport,
    HealthStatus,
    check_black,
    check_build,
    check_ci_status,
    check_code_metrics,
    check_coverage,
    check_dependencies,
    check_documentation,
    check_flake8,
    check_git_status,
    check_isort,
    check_mypy,
    check_security,
    check_tests,
    find_repo_root,
    generate_report,
    health_group,
    run_command,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_repo(tmp_path: Path) -> Path:
    """Create a mock repository structure."""
    # Create git directory
    (tmp_path / ".git").mkdir()

    # Create src directory with Python files
    src_dir = tmp_path / "src" / "mypackage"
    src_dir.mkdir(parents=True)

    (src_dir / "__init__.py").write_text('"""My package."""\n')
    (src_dir / "main.py").write_text(
        '"""Main module."""\n\ndef hello():\n    """Say hello."""\n    print("Hello")\n'
    )

    # Create tests directory
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_main.py").write_text(
        'def test_hello():\n    """Test hello."""\n    assert True\n'
    )

    # Create docs directory
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Documentation\n")

    # Create README
    (tmp_path / "README.md").write_text("# My Project\n")

    # Create pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "mypackage"\nversion = "1.0.0"\n'
    )

    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


# =============================================================================
# Test HealthStatus Enum
# =============================================================================


class TestHealthStatus:
    """Tests for HealthStatus enum."""

    def test_status_values(self):
        """Test that status values are correct."""
        assert HealthStatus.PASSING.value == "passing"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.FAILING.value == "failing"
        assert HealthStatus.SKIPPED.value == "skipped"
        assert HealthStatus.ERROR.value == "error"


# =============================================================================
# Test CheckResult Dataclass
# =============================================================================


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_basic_result(self):
        """Test creating a basic check result."""
        result = CheckResult(
            name="Test Check",
            status=HealthStatus.PASSING,
            message="All tests passed",
        )
        assert result.name == "Test Check"
        assert result.status == HealthStatus.PASSING
        assert result.message == "All tests passed"
        assert result.details is None
        assert result.metrics == {}
        assert result.suggestions == []
        assert result.duration_ms == 0.0

    def test_full_result(self):
        """Test creating a result with all fields."""
        result = CheckResult(
            name="Coverage",
            status=HealthStatus.WARNING,
            message="Coverage is low",
            details="Only 50% covered",
            metrics={"coverage": 50, "target": 80},
            suggestions=["Add more tests"],
            duration_ms=123.45,
        )
        assert result.name == "Coverage"
        assert result.details == "Only 50% covered"
        assert result.metrics["coverage"] == 50
        assert "Add more tests" in result.suggestions
        assert result.duration_ms == 123.45


# =============================================================================
# Test HealthReport Dataclass
# =============================================================================


class TestHealthReport:
    """Tests for HealthReport dataclass."""

    def test_basic_report(self):
        """Test creating a basic health report."""
        report = HealthReport(
            timestamp="2025-01-01T00:00:00",
            repo_path="/path/to/repo",
            checks=[],
        )
        assert report.timestamp == "2025-01-01T00:00:00"
        assert report.repo_path == "/path/to/repo"
        assert report.checks == []
        assert report.overall_status == HealthStatus.PASSING

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        check = CheckResult(
            name="Test",
            status=HealthStatus.PASSING,
            message="OK",
            metrics={"count": 10},
        )
        report = HealthReport(
            timestamp="2025-01-01T00:00:00",
            repo_path="/path/to/repo",
            checks=[check],
            summary={"passing": 1, "failing": 0},
            overall_status=HealthStatus.PASSING,
            total_duration_ms=100.0,
        )

        result = report.to_dict()

        assert result["timestamp"] == "2025-01-01T00:00:00"
        assert result["repo_path"] == "/path/to/repo"
        assert result["overall_status"] == "passing"
        assert result["summary"] == {"passing": 1, "failing": 0}
        assert len(result["checks"]) == 1
        assert result["checks"][0]["name"] == "Test"
        assert result["checks"][0]["status"] == "passing"


# =============================================================================
# Test Helper Functions
# =============================================================================


class TestRunCommand:
    """Tests for run_command function."""

    def test_successful_command(self):
        """Test running a successful command."""
        code, stdout, stderr = run_command(["echo", "hello"])
        assert code == 0
        assert "hello" in stdout
        assert stderr == ""

    def test_failing_command(self):
        """Test running a failing command."""
        code, stdout, stderr = run_command(["ls", "/nonexistent_path_12345"])
        assert code != 0

    def test_command_not_found(self):
        """Test running a non-existent command."""
        code, stdout, stderr = run_command(["nonexistent_command_12345"])
        assert code == -2
        assert "not found" in stderr.lower()

    def test_command_with_timeout(self):
        """Test command timeout handling."""
        # This should timeout very quickly
        code, stdout, stderr = run_command(["sleep", "10"], timeout=1)
        assert code == -1
        assert "timed out" in stderr.lower()


class TestFindRepoRoot:
    """Tests for find_repo_root function."""

    def test_finds_git_repo(self, mock_repo: Path):
        """Test finding a git repository root."""
        with patch("mcli.self.health_cmd.Path.cwd", return_value=mock_repo / "src"):
            root = find_repo_root()
            # Should find the parent with .git
            assert (root / ".git").exists() or root == Path.cwd()


# =============================================================================
# Test Individual Check Functions
# =============================================================================


class TestCheckGitStatus:
    """Tests for check_git_status function."""

    def test_not_a_git_repo(self, tmp_path: Path):
        """Test checking a non-git directory."""
        result = check_git_status(tmp_path)
        assert result.status == HealthStatus.ERROR
        assert "not a git repository" in result.message.lower()

    @patch("mcli.self.health_cmd.run_command")
    def test_clean_repo(self, mock_run: MagicMock, mock_repo: Path):
        """Test checking a clean git repo."""
        mock_run.side_effect = [
            (0, "main\n", ""),  # branch
            (0, "", ""),  # status --porcelain
            (0, "0\n", ""),  # rev-list
            (0, "abc123 Initial commit (1 hour ago)\n", ""),  # log
        ]

        result = check_git_status(mock_repo)

        assert result.status == HealthStatus.PASSING
        assert result.metrics["branch"] == "main"
        assert result.metrics["uncommitted_changes"] == 0

    @patch("mcli.self.health_cmd.run_command")
    def test_dirty_repo(self, mock_run: MagicMock, mock_repo: Path):
        """Test checking a repo with uncommitted changes."""
        mock_run.side_effect = [
            (0, "main\n", ""),  # branch
            (0, " M file.py\n?? new.txt\n", ""),  # status --porcelain
            (0, "2\n", ""),  # rev-list
            (0, "abc123 Initial commit (1 hour ago)\n", ""),  # log
        ]

        result = check_git_status(mock_repo)

        assert result.status == HealthStatus.WARNING
        assert result.metrics["uncommitted_changes"] == 2
        assert result.metrics["unpushed_commits"] == 2
        assert len(result.suggestions) > 0


class TestCheckCodeMetrics:
    """Tests for check_code_metrics function."""

    def test_counts_python_files(self, mock_repo: Path):
        """Test counting Python files and lines."""
        result = check_code_metrics(mock_repo)

        assert result.status == HealthStatus.PASSING
        assert result.metrics["python_files"] >= 2  # At least __init__.py and main.py
        assert result.metrics["code_lines"] > 0
        assert result.metrics["functions"] >= 1  # hello function

    def test_empty_directory(self, tmp_path: Path):
        """Test with empty directory."""
        (tmp_path / "src").mkdir()
        result = check_code_metrics(tmp_path)

        assert result.status == HealthStatus.PASSING
        assert result.metrics["python_files"] == 0


class TestCheckDocumentation:
    """Tests for check_documentation function."""

    def test_complete_docs(self, mock_repo: Path):
        """Test with complete documentation."""
        # Add more doc files
        (mock_repo / "CONTRIBUTING.md").write_text("# Contributing\n")
        (mock_repo / "CHANGELOG.md").write_text("# Changelog\n")
        (mock_repo / "CLAUDE.md").write_text("# Claude\n")

        result = check_documentation(mock_repo)

        assert result.status == HealthStatus.PASSING
        assert result.metrics["key_docs_present"] == 5

    def test_missing_docs(self, tmp_path: Path):
        """Test with missing documentation."""
        result = check_documentation(tmp_path)

        assert result.status == HealthStatus.WARNING
        assert len(result.suggestions) > 0


class TestCheckBlack:
    """Tests for check_black function."""

    @patch("mcli.self.health_cmd.run_command")
    def test_black_not_installed(self, mock_run: MagicMock, mock_repo: Path):
        """Test when black is not installed."""
        mock_run.return_value = (1, "", "No module named black")

        result = check_black(mock_repo)

        assert result.status == HealthStatus.SKIPPED
        assert "not installed" in result.message

    @patch("mcli.self.health_cmd.run_command")
    def test_black_passes(self, mock_run: MagicMock, mock_repo: Path):
        """Test when all files are formatted."""
        mock_run.side_effect = [
            (0, "black, 24.0.0\n", ""),  # version check
            (0, "", ""),  # black --check
        ]

        result = check_black(mock_repo)

        assert result.status == HealthStatus.PASSING

    @patch("mcli.self.health_cmd.run_command")
    def test_black_fails(self, mock_run: MagicMock, mock_repo: Path):
        """Test when files need formatting."""
        mock_run.side_effect = [
            (0, "black, 24.0.0\n", ""),  # version check
            (1, "would reformat file1.py\nwould reformat file2.py\n", ""),  # black --check
        ]

        result = check_black(mock_repo)

        assert result.status == HealthStatus.FAILING
        assert result.metrics["files_to_format"] == 2


class TestCheckTests:
    """Tests for check_tests function."""

    @patch("mcli.self.health_cmd.run_command")
    def test_pytest_not_installed(self, mock_run: MagicMock, mock_repo: Path):
        """Test when pytest is not installed."""
        mock_run.return_value = (1, "", "No module named pytest")

        result = check_tests(mock_repo)

        assert result.status == HealthStatus.SKIPPED

    @patch("mcli.self.health_cmd.run_command")
    def test_all_tests_pass(self, mock_run: MagicMock, mock_repo: Path):
        """Test when all tests pass."""
        mock_run.side_effect = [
            (0, "pytest 8.0.0\n", ""),  # version check
            (0, "10 passed, 2 skipped\n", ""),  # pytest
        ]

        result = check_tests(mock_repo)

        assert result.status == HealthStatus.PASSING
        assert result.metrics["passed"] == 10
        assert result.metrics["failed"] == 0
        assert result.metrics["skipped"] == 2

    @patch("mcli.self.health_cmd.run_command")
    def test_some_tests_fail(self, mock_run: MagicMock, mock_repo: Path):
        """Test when some tests fail (<=5 failures = WARNING, >5 = FAILING)."""
        mock_run.side_effect = [
            (0, "pytest 8.0.0\n", ""),  # version check
            (1, "8 passed, 2 failed, 1 skipped\n", ""),  # pytest
        ]

        result = check_tests(mock_repo)

        # Small number of failures (2 <= 5) is a warning, not failing
        assert result.status == HealthStatus.WARNING
        assert result.metrics["passed"] == 8
        assert result.metrics["failed"] == 2


class TestCheckSecurity:
    """Tests for check_security function."""

    @patch("mcli.self.health_cmd.run_command")
    def test_no_security_issues(self, mock_run: MagicMock, mock_repo: Path):
        """Test when no security issues are found."""
        mock_run.side_effect = [
            (0, "bandit 1.7.0\n", ""),  # version check
            (0, '{"results": []}', ""),  # bandit scan
        ]

        result = check_security(mock_repo)

        assert result.status == HealthStatus.PASSING
        assert result.metrics["total"] == 0

    @patch("mcli.self.health_cmd.run_command")
    def test_high_severity_issues(self, mock_run: MagicMock, mock_repo: Path):
        """Test when high severity issues are found."""
        mock_run.side_effect = [
            (0, "bandit 1.7.0\n", ""),  # version check
            (
                0,
                '{"results": [{"issue_severity": "HIGH"}, {"issue_severity": "MEDIUM"}]}',
                "",
            ),
        ]

        result = check_security(mock_repo)

        assert result.status == HealthStatus.FAILING
        assert result.metrics["high"] == 1
        assert result.metrics["medium"] == 1


# =============================================================================
# Test Report Generation
# =============================================================================


class TestGenerateReport:
    """Tests for generate_report function."""

    @patch("mcli.self.health_cmd.check_git_status")
    @patch("mcli.self.health_cmd.check_code_metrics")
    @patch("mcli.self.health_cmd.check_black")
    @patch("mcli.self.health_cmd.check_isort")
    @patch("mcli.self.health_cmd.check_flake8")
    def test_quick_report(
        self,
        mock_flake8: MagicMock,
        mock_isort: MagicMock,
        mock_black: MagicMock,
        mock_metrics: MagicMock,
        mock_git: MagicMock,
        mock_repo: Path,
    ):
        """Test generating a quick report."""
        # Set up mocks
        mock_git.return_value = CheckResult("Git", HealthStatus.PASSING, "OK")
        mock_metrics.return_value = CheckResult("Metrics", HealthStatus.PASSING, "OK")
        mock_black.return_value = CheckResult("Black", HealthStatus.PASSING, "OK")
        mock_isort.return_value = CheckResult("isort", HealthStatus.PASSING, "OK")
        mock_flake8.return_value = CheckResult("Flake8", HealthStatus.PASSING, "OK")

        report = generate_report(mock_repo, quick=True, skip_tests=True)

        assert report.overall_status == HealthStatus.PASSING
        assert len(report.checks) >= 5

    @patch("mcli.self.health_cmd.check_git_status")
    @patch("mcli.self.health_cmd.check_code_metrics")
    @patch("mcli.self.health_cmd.check_black")
    @patch("mcli.self.health_cmd.check_isort")
    @patch("mcli.self.health_cmd.check_flake8")
    def test_report_with_failures(
        self,
        mock_flake8: MagicMock,
        mock_isort: MagicMock,
        mock_black: MagicMock,
        mock_metrics: MagicMock,
        mock_git: MagicMock,
        mock_repo: Path,
    ):
        """Test report with failing checks."""
        mock_git.return_value = CheckResult("Git", HealthStatus.PASSING, "OK")
        mock_metrics.return_value = CheckResult("Metrics", HealthStatus.PASSING, "OK")
        mock_black.return_value = CheckResult("Black", HealthStatus.FAILING, "Needs format")
        mock_isort.return_value = CheckResult("isort", HealthStatus.PASSING, "OK")
        mock_flake8.return_value = CheckResult("Flake8", HealthStatus.WARNING, "Issues")

        report = generate_report(mock_repo, quick=True, skip_tests=True)

        assert report.overall_status == HealthStatus.FAILING
        assert report.summary["failing"] >= 1
        assert report.summary["warning"] >= 1


# =============================================================================
# Test CLI Commands
# =============================================================================


class TestHealthCLI:
    """Tests for health CLI commands."""

    def test_help_command(self, runner: CliRunner):
        """Test health --help command."""
        result = runner.invoke(health_group, ["--help"])
        assert result.exit_code == 0
        assert "Repository health analysis" in result.output

    def test_check_help(self, runner: CliRunner):
        """Test health check --help command."""
        result = runner.invoke(health_group, ["check", "--help"])
        assert result.exit_code == 0
        assert "comprehensive health checks" in result.output.lower()

    def test_fix_help(self, runner: CliRunner):
        """Test health fix --help command."""
        result = runner.invoke(health_group, ["fix", "--help"])
        assert result.exit_code == 0
        assert "Auto-fix" in result.output

    def test_report_help(self, runner: CliRunner):
        """Test health report --help command."""
        result = runner.invoke(health_group, ["report", "--help"])
        assert result.exit_code == 0
        assert "Generate a health report" in result.output

    @patch("mcli.self.health_cmd.generate_report")
    @patch("mcli.self.health_cmd.find_repo_root")
    def test_check_json_output(
        self,
        mock_root: MagicMock,
        mock_report: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ):
        """Test health check with JSON output."""
        mock_root.return_value = tmp_path
        mock_report.return_value = HealthReport(
            timestamp="2025-01-01T00:00:00",
            repo_path=str(tmp_path),
            checks=[],
            summary={"passing": 0, "failing": 0, "warning": 0, "skipped": 0, "error": 0},
            overall_status=HealthStatus.PASSING,
        )

        result = runner.invoke(health_group, ["check", "--json", "--skip-tests"])

        assert result.exit_code == 0
        # The JSON output should contain valid JSON somewhere in the output
        # Find the JSON part by looking for the opening brace
        output_lines = result.output.strip().split("\n")
        json_content = None
        for i, line in enumerate(output_lines):
            if line.strip().startswith("{"):
                # Join from here to end to get the full JSON
                json_content = "\n".join(output_lines[i:])
                break

        assert json_content is not None, f"No JSON found in output: {result.output}"
        parsed = json.loads(json_content)
        assert "timestamp" in parsed
        assert "overall_status" in parsed

    @patch("mcli.self.health_cmd.run_command")
    @patch("mcli.self.health_cmd.find_repo_root")
    def test_fix_dry_run(
        self,
        mock_root: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
        tmp_path: Path,
    ):
        """Test health fix --dry-run."""
        mock_root.return_value = tmp_path

        result = runner.invoke(health_group, ["fix", "--dry-run"])

        assert result.exit_code == 0
        assert "Would run" in result.output
        assert "Dry run complete" in result.output


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestHealthIntegration:
    """Integration tests for health command."""

    def test_check_on_real_repo(self, runner: CliRunner):
        """Test running health check on the actual repo."""
        result = runner.invoke(health_group, ["check", "--quick", "--skip-tests"])

        # Should run without crashing
        assert result.exit_code in [0, 1]  # Can fail if issues exist
        assert "Check Results" in result.output or "Repository Health" in result.output
