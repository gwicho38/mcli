"""Regression tests for stem-collision handling in the lockfile.

Bug: `generate_lockfile` keyed commands by bare ``script_path.stem``, so two
scripts sharing a stem (e.g. ``commit.py`` and ``commit.sh``, or the same name
in different group subdirectories) collapsed to a single lockfile entry — the
later one silently overwrote the earlier. `mcli sync now` therefore dropped
every colliding script before push.

The lockfile must give every discovered script a distinct entry, using the
``name:lang`` disambiguation convention already used by ``mcli list``/``run``
(see docs/features/LANGUAGE_SUFFIX.md).
"""

import json
from pathlib import Path

from mcli.lib.script_loader import ScriptLoader

PY = "#!/usr/bin/env python3\n# @description: py impl\nprint('py')\n"
SH = "#!/usr/bin/env bash\n# @description: sh impl\necho sh\n"


def _commands(loader: ScriptLoader) -> dict:
    assert loader.save_lockfile() is True
    return json.loads(loader.lockfile_path.read_text())["commands"]


def test_cross_language_collision_keeps_both(tmp_path):
    """commit.py and commit.sh must both survive, suffixed by language."""
    wd = tmp_path / "workflows"
    (wd / "dotfiles").mkdir(parents=True)
    (wd / "dotfiles" / "commit.py").write_text(PY)
    (wd / "dotfiles" / "commit.sh").write_text(SH)

    cmds = _commands(ScriptLoader(wd))

    # Both implementations are tracked under distinct, language-suffixed keys.
    assert "commit:py" in cmds, cmds.keys()
    assert "commit:sh" in cmds, cmds.keys()
    assert cmds["commit:py"]["file"] == "dotfiles/commit.py"
    assert cmds["commit:sh"]["file"] == "dotfiles/commit.sh"
    # No bare 'commit' that silently shadows one of them.
    assert "commit" not in cmds


def test_unique_stem_stays_bare(tmp_path):
    """A stem with no collision keeps its bare name for ergonomics."""
    wd = tmp_path / "workflows"
    wd.mkdir()
    (wd / "deploy.py").write_text(PY)

    cmds = _commands(ScriptLoader(wd))
    assert "deploy" in cmds
    assert cmds["deploy"]["file"] == "deploy.py"


def test_same_name_same_ext_different_dirs_not_dropped(tmp_path):
    """Two scripts with identical name AND extension in different dirs must
    each get a distinct entry — neither may be silently dropped."""
    wd = tmp_path / "workflows"
    (wd / "a").mkdir(parents=True)
    (wd / "b").mkdir(parents=True)
    (wd / "a" / "videos.py").write_text(PY)
    (wd / "b" / "videos.py").write_text(SH.replace("echo sh", "print('b')"))

    cmds = _commands(ScriptLoader(wd))

    # Every distinct file is represented exactly once.
    files = sorted(v["file"] for v in cmds.values())
    assert files == ["a/videos.py", "b/videos.py"], files
    assert len(cmds) == 2, cmds.keys()


def test_no_script_dropped_overall(tmp_path):
    """Total lockfile entries == number of discovered script files."""
    wd = tmp_path / "workflows"
    (wd / "g1").mkdir(parents=True)
    (wd / "g2").mkdir(parents=True)
    (wd / "g1" / "build.py").write_text(PY)
    (wd / "g1" / "build.sh").write_text(SH)
    (wd / "g2" / "build.py").write_text(PY)  # collides with g1/build.py on name+ext
    (wd / "solo.sh").write_text(SH)

    loader = ScriptLoader(wd)
    n_files = len(loader.discover_scripts())
    cmds = _commands(loader)
    assert len(cmds) == n_files == 4, (len(cmds), n_files, list(cmds.keys()))


def test_verify_lockfile_clean_after_save_with_collisions(tmp_path):
    """`sync diff`/`status` (verify_lockfile) must not report false drift when
    colliding scripts are tracked under name:lang keys."""
    wd = tmp_path / "workflows"
    (wd / "dotfiles").mkdir(parents=True)
    (wd / "dotfiles" / "commit.py").write_text(PY)
    (wd / "dotfiles" / "commit.sh").write_text(SH)
    (wd / "deploy.py").write_text(PY)

    loader = ScriptLoader(wd)
    assert loader.save_lockfile() is True

    result = loader.verify_lockfile()
    assert result["missing"] == [], result["missing"]
    assert result["extra"] == [], result["extra"]
    assert result["hash_mismatch"] == [], result["hash_mismatch"]
    assert result["valid"] is True


def test_sync_status_shows_collided_scripts_as_synced(tmp_path):
    """`mcli sync status` must mark colliding scripts synced (not 'unlocked')
    and display their disambiguated names."""
    from unittest.mock import patch

    from click.testing import CliRunner

    from mcli.app.sync_cmd import sync_group

    wd = tmp_path / "workflows"
    (wd / "dotfiles").mkdir(parents=True)
    (wd / "dotfiles" / "commit.py").write_text(PY)
    (wd / "dotfiles" / "commit.sh").write_text(SH)

    runner = CliRunner()
    with patch("mcli.app.sync_cmd.get_custom_commands_dir", return_value=wd):
        assert runner.invoke(sync_group, ["update"]).exit_code == 0
        result = runner.invoke(sync_group, ["status"])
        diff = runner.invoke(sync_group, ["diff"])

    assert result.exit_code == 0, result.output
    assert "unlocked" not in result.output, result.output
    assert "commit:py" in result.output and "commit:sh" in result.output, result.output
    # diff right after update => in sync, no spurious added/removed.
    assert "Added scripts" not in diff.output, diff.output
    assert "Removed scripts" not in diff.output, diff.output
