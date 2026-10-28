"""The hardcoded-strings hook checks only the lines a commit adds or changes.

It used to check whole files, so touching one line of a file with older
violations failed the commit on strings the commit never changed.
"""

import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools" / "lint_hardcoded_strings.py"

OLD = 'def old():\n    return "this existing message has many words in it"\n'
NEW_LINE = 'def new():\n    return "a brand new message with several words"\n'


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "mod.py").write_text(OLD)
    _git(tmp_path, "add", "mod.py")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _lint(repo, *args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args, "mod.py"], cwd=repo, capture_output=True, text=True
    )


def test_whole_file_mode_still_reports_existing_strings(repo):
    out = _lint(repo)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "existing message" in out.stdout


def test_an_untouched_old_string_does_not_fail_the_commit(repo):
    (repo / "mod.py").write_text(OLD + "\n\nX = 1\n")
    _git(repo, "add", "mod.py")
    out = _lint(repo, "--changed-lines-only")
    assert out.returncode == 0, out.stdout + out.stderr


def test_a_new_hardcoded_string_still_fails(repo):
    (repo / "mod.py").write_text(OLD + "\n\n" + NEW_LINE)
    _git(repo, "add", "mod.py")
    out = _lint(repo, "--changed-lines-only")
    assert out.returncode == 1, out.stdout + out.stderr
    assert "brand new message" in out.stdout
    assert "existing message" not in out.stdout
