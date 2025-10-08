"""
Unit tests for mcli.workflow.git_commit.commands module

NOTE: This module has been migrated to portable JSON commands.
Tests are skipped as the Python module no longer exists.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

# Skip all tests in this module - git_commit commands now loaded from JSON
pytestmark = pytest.mark.skip(reason="git_commit commands migrated to portable JSON format")


class TestGitCommitWorkflow:
    """Test suite for GitCommitWorkflow"""

    def test_init_with_valid_repo(self):
        """Test initialization with valid git repository"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a git repo
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)

            assert workflow.repo_path == repo_path
            assert not workflow.use_ai
            assert workflow.ai_service is None

    def test_init_with_invalid_repo(self):
        """Test initialization with invalid git repository"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Not a git repository"):
                GitCommitWorkflow(repo_path=tmpdir, use_ai=False)

    def test_init_with_ai_enabled(self):
        """Test initialization with AI service enabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            with patch('mcli.workflow.git_commit.commands.GitCommitAIService'):
                workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=True)

                assert workflow.use_ai
                assert workflow.ai_service is not None

    def test_init_uses_current_dir_when_no_path(self):
        """Test that initialization uses current directory when no path provided"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            with patch('pathlib.Path.cwd', return_value=repo_path):
                workflow = GitCommitWorkflow(use_ai=False)

                assert workflow.repo_path == repo_path

    @patch('subprocess.run')
    def test_get_git_status_with_changes(self, mock_run):
        """Test getting git status with changes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock git status output - format: XY filename where XY is 2-char status
            # Don't add leading/trailing whitespace as strip() will remove it
            mock_run.return_value = Mock(
                stdout=" M file1.py\nA  file2.py\nD  file3.py\n?? file4.py\n",
                returncode=0
            )

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            status = workflow.get_git_status()

            assert status["has_changes"]
            assert status["total_files"] == 4
            assert "file1.py" in status["changes"]["modified"]
            assert "file2.py" in status["changes"]["added"]
            assert "file3.py" in status["changes"]["deleted"]
            assert "file4.py" in status["changes"]["untracked"]

    @patch('subprocess.run')
    def test_get_git_status_no_changes(self, mock_run):
        """Test getting git status with no changes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock empty git status
            mock_run.return_value = Mock(stdout="", returncode=0)

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            status = workflow.get_git_status()

            assert not status["has_changes"]
            assert status["total_files"] == 0
            assert len(status["changes"]["modified"]) == 0

    @patch('subprocess.run')
    def test_get_git_status_error(self, mock_run):
        """Test handling git status error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock git command failure
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "status"])

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)

            with pytest.raises(RuntimeError, match="Failed to get git status"):
                workflow.get_git_status()

    @patch('subprocess.run')
    def test_get_git_diff(self, mock_run):
        """Test getting git diff"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock git diff outputs
            staged_diff = "diff --git a/file1.py\n+new line"
            unstaged_diff = "diff --git a/file2.py\n-old line"

            mock_run.side_effect = [
                Mock(stdout=staged_diff, returncode=0),
                Mock(stdout=unstaged_diff, returncode=0),
            ]

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            diff = workflow.get_git_diff()

            assert staged_diff in diff
            assert unstaged_diff in diff

    @patch('subprocess.run')
    def test_get_git_diff_error(self, mock_run):
        """Test handling git diff error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock git command failure
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "diff"])

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)

            with pytest.raises(RuntimeError, match="Failed to get git diff"):
                workflow.get_git_diff()

    @patch('subprocess.run')
    def test_generate_commit_message_without_ai(self, mock_run):
        """Test generating commit message without AI"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)

            # Prepare changes dict matching what get_git_status returns
            changes = {
                "has_changes": True,
                "changes": {
                    "modified": ["file1.py"],
                    "added": ["file2.py"],
                    "deleted": [],
                    "renamed": [],
                    "untracked": []
                },
                "total_files": 2
            }
            diff_content = "diff content"

            message = workflow.generate_commit_message(changes, diff_content)

            assert message is not None
            assert isinstance(message, str)
            assert len(message) > 0
            assert "file2.py" in message or "file1.py" in message or "Update" in message

    @patch('subprocess.run')
    def test_generate_commit_message_with_ai(self, mock_run):
        """Test generating commit message with AI"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            with patch('mcli.workflow.git_commit.commands.GitCommitAIService') as mock_ai:
                mock_ai_instance = Mock()
                mock_ai_instance.generate_commit_message.return_value = "AI generated commit message"
                mock_ai.return_value = mock_ai_instance

                workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=True)

                # Prepare changes and diff
                changes = {
                    "has_changes": True,
                    "changes": {
                        "modified": ["file1.py"],
                        "added": [],
                        "deleted": [],
                        "renamed": [],
                        "untracked": []
                    },
                    "total_files": 1
                }
                diff_content = "diff content"

                message = workflow.generate_commit_message(changes, diff_content)

                assert message == "AI generated commit message"
                mock_ai_instance.generate_commit_message.assert_called_once()

    @patch('subprocess.run')
    def test_create_commit(self, mock_run):
        """Test creating a commit"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock successful commit
            mock_run.return_value = Mock(stdout="", returncode=0)

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            result = workflow.create_commit("test commit message")

            assert result
            # Verify git commit was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "git" in call_args[0][0]
            assert "commit" in call_args[0][0]

    @patch('subprocess.run')
    def test_create_commit_failure(self, mock_run):
        """Test handling commit failure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock commit failure
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "commit"])

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            result = workflow.create_commit("test message")

            # create_commit returns False on failure, doesn't raise
            assert result is False

    @patch('subprocess.run')
    def test_stage_all_changes(self, mock_run):
        """Test staging all changes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock successful staging
            mock_run.return_value = Mock(stdout="", returncode=0)

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            result = workflow.stage_all_changes()

            assert result is True
            # Verify git add was called with .
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["git", "add", "."]

    @patch('subprocess.run')
    def test_stage_all_changes_failure(self, mock_run):
        """Test staging all changes failure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock staging failure
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "add"])

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            result = workflow.stage_all_changes()

            assert result is False

    @patch('subprocess.run')
    def test_parse_git_status_with_renamed_files(self, mock_run):
        """Test parsing git status with renamed files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock git status with renamed file
            mock_run.return_value = Mock(
                stdout="R  old_name.py -> new_name.py\n",
                returncode=0
            )

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            status = workflow.get_git_status()

            assert "old_name.py -> new_name.py" in status["changes"]["renamed"]

    @patch('subprocess.run')
    def test_parse_git_status_with_mixed_changes(self, mock_run):
        """Test parsing git status with multiple types of changes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".git").mkdir()

            # Mock complex git status
            mock_run.return_value = Mock(
                stdout=" M modified.py\nA  added.py\nD  deleted.py\nR  old -> new\n?? untracked.py\nMM both.py\n",
                returncode=0
            )

            workflow = GitCommitWorkflow(repo_path=str(repo_path), use_ai=False)
            status = workflow.get_git_status()

            assert status["has_changes"]
            assert status["total_files"] == 6
            assert len(status["changes"]["modified"]) >= 1
            assert len(status["changes"]["added"]) >= 1
            assert len(status["changes"]["deleted"]) >= 1
            assert len(status["changes"]["renamed"]) >= 1
            assert len(status["changes"]["untracked"]) >= 1
