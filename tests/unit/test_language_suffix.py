"""
Unit tests for language suffix disambiguation.

Tests the colon-delimited suffix system that allows users to disambiguate
commands when multiple scripts share the same stem (e.g. backup.py and backup.sh).

Covers:
- parse_command_name() parsing logic
- find_scripts_by_stem() discovery
- ScopedWorkflowsGroup.list_commands() with and without duplicates
- ScopedWorkflowsGroup.get_command() with suffix, without suffix, and ambiguous
"""

import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from mcli.lib.script_loader import (
    LANGUAGE_SUFFIXES,
    LANGUAGE_TO_SUFFIX,
    ScriptLoader,
    parse_command_name,
)


class TestParseCommandName:
    """Test parse_command_name() parsing logic."""

    def test_bare_name(self):
        """Bare name returns (name, None)."""
        base, lang = parse_command_name("backup")
        assert base == "backup"
        assert lang is None

    def test_python_suffix(self):
        """'backup:py' → ('backup', 'python')."""
        base, lang = parse_command_name("backup:py")
        assert base == "backup"
        assert lang == "python"

    def test_python_long_suffix(self):
        """'backup:python' → ('backup', 'python')."""
        base, lang = parse_command_name("backup:python")
        assert base == "backup"
        assert lang == "python"

    def test_shell_suffix(self):
        """'backup:sh' → ('backup', 'shell')."""
        base, lang = parse_command_name("backup:sh")
        assert base == "backup"
        assert lang == "shell"

    def test_bash_suffix(self):
        """'backup:bash' → ('backup', 'shell')."""
        base, lang = parse_command_name("backup:bash")
        assert base == "backup"
        assert lang == "shell"

    def test_javascript_suffix(self):
        """'deploy:js' → ('deploy', 'javascript')."""
        base, lang = parse_command_name("deploy:js")
        assert base == "deploy"
        assert lang == "javascript"

    def test_typescript_suffix(self):
        """'deploy:ts' → ('deploy', 'typescript')."""
        base, lang = parse_command_name("deploy:ts")
        assert base == "deploy"
        assert lang == "typescript"

    def test_ipynb_suffix(self):
        """'analysis:ipynb' → ('analysis', 'ipynb')."""
        base, lang = parse_command_name("analysis:ipynb")
        assert base == "analysis"
        assert lang == "ipynb"

    def test_unknown_suffix_treated_as_bare(self):
        """Unknown suffix is treated as part of the bare name."""
        base, lang = parse_command_name("backup:xyz")
        assert base == "backup:xyz"
        assert lang is None

    def test_rsplit_with_multiple_colons(self):
        """Only the last colon is split: 'my:cmd:sh' → ('my:cmd', 'shell')."""
        base, lang = parse_command_name("my:cmd:sh")
        assert base == "my:cmd"
        assert lang == "shell"

    def test_case_insensitive_suffix(self):
        """Suffix matching is case insensitive."""
        base, lang = parse_command_name("backup:PY")
        assert base == "backup"
        assert lang == "python"

    def test_empty_name(self):
        """Empty string returns ('', None)."""
        base, lang = parse_command_name("")
        assert base == ""
        assert lang is None

    def test_colon_only(self):
        """':' alone returns (':', None) since empty suffix isn't recognized."""
        base, lang = parse_command_name(":")
        assert base == ":"
        assert lang is None


class TestLanguageMappings:
    """Test that the mapping dictionaries are consistent."""

    def test_language_to_suffix_covers_all_languages(self):
        """Every unique language in LANGUAGE_SUFFIXES has a reverse mapping."""
        unique_languages = set(LANGUAGE_SUFFIXES.values())
        for lang in unique_languages:
            assert lang in LANGUAGE_TO_SUFFIX, f"Missing reverse mapping for '{lang}'"

    def test_roundtrip(self):
        """The canonical suffix for each language maps back to that language."""
        for lang, suffix in LANGUAGE_TO_SUFFIX.items():
            assert LANGUAGE_SUFFIXES[suffix] == lang


class TestFindScriptsByStem:
    """Test ScriptLoader.find_scripts_by_stem()."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workflows_dir = Path(self.temp_dir) / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.loader = ScriptLoader(self.workflows_dir)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_script(self, name: str, content: str = "#!/usr/bin/env bash\necho hi\n") -> Path:
        script_path = self.workflows_dir / name
        script_path.write_text(content)
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
        return script_path

    def test_finds_both_variants(self):
        """With backup.py and backup.sh, find_scripts_by_stem('backup') returns both."""
        self._create_script("backup.py", "#!/usr/bin/env python3\nprint('py')\n")
        self._create_script("backup.sh", "#!/usr/bin/env bash\necho sh\n")

        matches = self.loader.find_scripts_by_stem("backup")
        assert len(matches) == 2
        stems = {p.suffix for p in matches}
        assert stems == {".py", ".sh"}

    def test_finds_single(self):
        """With only backup.py, find_scripts_by_stem('backup') returns one."""
        self._create_script("backup.py", "#!/usr/bin/env python3\nprint('py')\n")

        matches = self.loader.find_scripts_by_stem("backup")
        assert len(matches) == 1
        assert matches[0].suffix == ".py"

    def test_no_match(self):
        """With no matching scripts, returns empty list."""
        self._create_script("deploy.sh")
        matches = self.loader.find_scripts_by_stem("backup")
        assert matches == []

    def test_does_not_match_partial_stem(self):
        """'back' should not match 'backup.py'."""
        self._create_script("backup.py", "#!/usr/bin/env python3\nprint('py')\n")
        matches = self.loader.find_scripts_by_stem("back")
        assert matches == []


class TestWorkflowListCommandsWithDuplicates:
    """Test ScopedWorkflowsGroup.list_commands() duplicate-aware naming."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workflows_dir = Path(self.temp_dir) / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_script(self, name: str, content: str) -> Path:
        script_path = self.workflows_dir / name
        script_path.write_text(content)
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
        return script_path

    def test_duplicate_stems_get_suffixed(self):
        """When backup.py and backup.sh exist, list_commands returns backup:py and backup:sh."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script(
            "backup.py",
            "#!/usr/bin/env python3\nimport click\n@click.command()\ndef backup():\n    pass\n",
        )
        self._create_script("backup.sh", "#!/usr/bin/env bash\necho backup\n")

        group = ScopedWorkflowsGroup(name="test")

        # Mock context with workspace pointing to our temp dir
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with patch(
            "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
            return_value=self.workflows_dir,
        ):
            commands = group.list_commands(ctx)

        assert "backup:py" in commands
        assert "backup:sh" in commands
        assert "backup" not in commands

    def test_unique_stem_stays_bare(self):
        """When only deploy.sh exists, list_commands returns bare 'deploy'."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script("deploy.sh", "#!/usr/bin/env bash\necho deploy\n")

        group = ScopedWorkflowsGroup(name="test")
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with patch(
            "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
            return_value=self.workflows_dir,
        ):
            commands = group.list_commands(ctx)

        assert "deploy" in commands
        assert "deploy:sh" not in commands

    def test_mixed_unique_and_duplicate(self):
        """Mix of unique and duplicate stems handled correctly."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script(
            "backup.py",
            "#!/usr/bin/env python3\nimport click\n@click.command()\ndef backup():\n    pass\n",
        )
        self._create_script("backup.sh", "#!/usr/bin/env bash\necho backup\n")
        self._create_script("deploy.sh", "#!/usr/bin/env bash\necho deploy\n")

        group = ScopedWorkflowsGroup(name="test")
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with patch(
            "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
            return_value=self.workflows_dir,
        ):
            commands = group.list_commands(ctx)

        assert "backup:py" in commands
        assert "backup:sh" in commands
        assert "deploy" in commands
        assert "deploy:sh" not in commands


class TestWorkflowGetCommandWithSuffix:
    """Test ScopedWorkflowsGroup.get_command() with language suffixes."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workflows_dir = Path(self.temp_dir) / "workflows"
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_script(self, name: str, content: str) -> Path:
        script_path = self.workflows_dir / name
        script_path.write_text(content)
        script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
        return script_path

    def test_get_command_with_suffix_loads_correct_language(self):
        """'backup:sh' loads the shell version when both exist."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script(
            "backup.py",
            "#!/usr/bin/env python3\nimport click\n@click.command()\ndef backup():\n    click.echo('python')\n",
        )
        self._create_script("backup.sh", "#!/usr/bin/env bash\necho shell\n")

        group = ScopedWorkflowsGroup(name="test")
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with patch(
            "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
            return_value=self.workflows_dir,
        ):
            cmd = group.get_command(ctx, "backup:sh")

        assert cmd is not None

    def test_get_command_with_suffix_loads_python(self):
        """'backup:py' loads the python version when both exist."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script(
            "backup.py",
            "#!/usr/bin/env python3\nimport click\n@click.command()\ndef backup():\n    click.echo('python')\n",
        )
        self._create_script("backup.sh", "#!/usr/bin/env bash\necho shell\n")

        group = ScopedWorkflowsGroup(name="test")
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with patch(
            "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
            return_value=self.workflows_dir,
        ):
            cmd = group.get_command(ctx, "backup:py")

        assert cmd is not None

    def test_get_command_bare_name_single_match(self):
        """Bare name with single match loads directly, no warning."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script("deploy.sh", "#!/usr/bin/env bash\necho deploy\n")

        group = ScopedWorkflowsGroup(name="test")
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with patch(
            "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
            return_value=self.workflows_dir,
        ):
            cmd = group.get_command(ctx, "deploy")

        assert cmd is not None

    def test_get_command_bare_name_multiple_matches_shows_warning(self):
        """Bare name with multiple matches shows warning and returns first."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script(
            "backup.py",
            "#!/usr/bin/env python3\nimport click\n@click.command()\ndef backup():\n    click.echo('python')\n",
        )
        self._create_script("backup.sh", "#!/usr/bin/env bash\necho shell\n")

        group = ScopedWorkflowsGroup(name="test")
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with (
            patch(
                "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
                return_value=self.workflows_dir,
            ),
            patch("mcli.lib.ui.styling.warning") as mock_warning,
        ):
            cmd = group.get_command(ctx, "backup")

        assert cmd is not None
        mock_warning.assert_called_once()
        warning_msg = mock_warning.call_args[0][0]
        assert "backup:py" in warning_msg or "backup:sh" in warning_msg

    def test_get_command_no_match(self):
        """Non-existent command returns None."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script("deploy.sh", "#!/usr/bin/env bash\necho deploy\n")

        group = ScopedWorkflowsGroup(name="test")
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with patch(
            "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
            return_value=self.workflows_dir,
        ):
            cmd = group.get_command(ctx, "nonexistent")

        assert cmd is None

    def test_get_command_suffix_filters_to_nonexistent_language(self):
        """'backup:js' when only .py and .sh exist returns None."""
        from mcli.workflow.workflow import ScopedWorkflowsGroup

        self._create_script(
            "backup.py",
            "#!/usr/bin/env python3\nimport click\n@click.command()\ndef backup():\n    click.echo('python')\n",
        )
        self._create_script("backup.sh", "#!/usr/bin/env bash\necho shell\n")

        group = ScopedWorkflowsGroup(name="test")
        ctx = click.Context(group)
        ctx.params = {"is_global": False, "workspace": None}

        with patch(
            "mcli.workflow.workflow.ScopedWorkflowsGroup._get_workflows_dir",
            return_value=self.workflows_dir,
        ):
            cmd = group.get_command(ctx, "backup:js")

        assert cmd is None


class TestApplyDisplayNames:
    """Test the _apply_display_names helper in list_cmd."""

    def test_unique_names_stay_bare(self):
        from mcli.app.list_cmd import _apply_display_names

        workflows = [
            {"name": "deploy", "language": "shell"},
            {"name": "backup", "language": "python"},
        ]
        _apply_display_names(workflows)
        assert workflows[0]["display_name"] == "deploy"
        assert workflows[1]["display_name"] == "backup"

    def test_duplicate_names_get_suffixed(self):
        from mcli.app.list_cmd import _apply_display_names

        workflows = [
            {"name": "backup", "language": "python"},
            {"name": "backup", "language": "shell"},
        ]
        _apply_display_names(workflows)
        assert workflows[0]["display_name"] == "backup:py"
        assert workflows[1]["display_name"] == "backup:sh"

    def test_mixed_unique_and_duplicate(self):
        from mcli.app.list_cmd import _apply_display_names

        workflows = [
            {"name": "backup", "language": "python"},
            {"name": "backup", "language": "shell"},
            {"name": "deploy", "language": "shell"},
        ]
        _apply_display_names(workflows)
        assert workflows[0]["display_name"] == "backup:py"
        assert workflows[1]["display_name"] == "backup:sh"
        assert workflows[2]["display_name"] == "deploy"

    def test_unknown_language_uses_question_mark(self):
        from mcli.app.list_cmd import _apply_display_names

        workflows = [
            {"name": "mystery", "language": "unknown_lang"},
            {"name": "mystery", "language": "python"},
        ]
        _apply_display_names(workflows)
        assert workflows[0]["display_name"] == "mystery:?"
        assert workflows[1]["display_name"] == "mystery:py"
