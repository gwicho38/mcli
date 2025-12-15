"""
Unit tests for mcli new command.

Tests cover:
- Command name validation
- Group name validation
- Language detection from file extensions
- Metadata detection and addition
- Template generation
- File import functionality
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcli.app.new_cmd import (
    EXIT_ERROR,
    EXIT_SUCCESS,
    _execute_new_command,
    add_metadata_to_script,
    detect_language_from_file,
    get_template,
    has_mcli_metadata,
    restructure_file_as_command,
    save_script,
    validate_command_name,
    validate_group_name,
)
from mcli.lib.constants import (
    ScriptCommentPrefixes,
    ScriptExtensions,
    ScriptLanguages,
    ScriptMetadataDefaults,
    ScriptMetadataKeys,
    ShellTypes,
)
from mcli.lib.errors import (
    InvalidCommandNameError,
    InvalidGroupNameError,
    UnsupportedFileTypeError,
    UnsupportedLanguageError,
)
from mcli.lib.types import ScriptTemplate


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidateCommandName:
    """Tests for validate_command_name function."""

    def test_valid_simple_name(self):
        """Valid simple command name."""
        assert validate_command_name("mycommand") == "mycommand"

    def test_valid_name_with_underscore(self):
        """Valid name with underscores."""
        assert validate_command_name("my_command") == "my_command"

    def test_valid_name_with_numbers(self):
        """Valid name with numbers."""
        assert validate_command_name("cmd123") == "cmd123"

    def test_normalizes_to_lowercase(self):
        """Uppercase is converted to lowercase."""
        assert validate_command_name("MyCommand") == "mycommand"

    def test_normalizes_dashes_to_underscores(self):
        """Dashes are converted to underscores."""
        assert validate_command_name("my-command") == "my_command"

    def test_invalid_starts_with_number(self):
        """Names starting with numbers are invalid."""
        with pytest.raises(InvalidCommandNameError) as exc_info:
            validate_command_name("123command")
        assert "123command" in str(exc_info.value)

    def test_invalid_contains_special_chars(self):
        """Names with special characters are invalid."""
        with pytest.raises(InvalidCommandNameError):
            validate_command_name("my@command")

    def test_invalid_empty_name(self):
        """Empty names are invalid."""
        with pytest.raises(InvalidCommandNameError):
            validate_command_name("")

    def test_invalid_starts_with_underscore(self):
        """Names starting with underscore are invalid."""
        with pytest.raises(InvalidCommandNameError):
            validate_command_name("_command")


class TestValidateGroupName:
    """Tests for validate_group_name function."""

    def test_valid_simple_name(self):
        """Valid simple group name."""
        assert validate_group_name("utils") == "utils"

    def test_valid_name_with_underscore(self):
        """Valid name with underscores."""
        assert validate_group_name("my_group") == "my_group"

    def test_normalizes_to_lowercase(self):
        """Uppercase is converted to lowercase."""
        assert validate_group_name("MyGroup") == "mygroup"

    def test_normalizes_dashes_to_underscores(self):
        """Dashes are converted to underscores."""
        assert validate_group_name("my-group") == "my_group"

    def test_invalid_starts_with_number(self):
        """Names starting with numbers are invalid."""
        with pytest.raises(InvalidGroupNameError):
            validate_group_name("123group")


# =============================================================================
# Language Detection Tests
# =============================================================================


class TestDetectLanguageFromFile:
    """Tests for detect_language_from_file function."""

    def test_detect_python(self, tmp_path):
        """Detect Python from .py extension."""
        file_path = tmp_path / "script.py"
        file_path.touch()
        assert detect_language_from_file(file_path) == ScriptLanguages.PYTHON

    def test_detect_shell(self, tmp_path):
        """Detect shell from .sh extension."""
        file_path = tmp_path / "script.sh"
        file_path.touch()
        assert detect_language_from_file(file_path) == ScriptLanguages.SHELL

    def test_detect_shell_bash(self, tmp_path):
        """Detect shell from .bash extension."""
        file_path = tmp_path / "script.bash"
        file_path.touch()
        assert detect_language_from_file(file_path) == ScriptLanguages.SHELL

    def test_detect_javascript(self, tmp_path):
        """Detect JavaScript from .js extension."""
        file_path = tmp_path / "script.js"
        file_path.touch()
        assert detect_language_from_file(file_path) == ScriptLanguages.JAVASCRIPT

    def test_detect_typescript(self, tmp_path):
        """Detect TypeScript from .ts extension."""
        file_path = tmp_path / "script.ts"
        file_path.touch()
        assert detect_language_from_file(file_path) == ScriptLanguages.TYPESCRIPT

    def test_detect_notebook(self, tmp_path):
        """Detect notebook from .ipynb extension."""
        file_path = tmp_path / "notebook.ipynb"
        file_path.touch()
        assert detect_language_from_file(file_path) == ScriptLanguages.IPYNB

    def test_unsupported_extension(self, tmp_path):
        """Unsupported extension raises error."""
        file_path = tmp_path / "file.txt"
        file_path.touch()
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            detect_language_from_file(file_path)
        assert ".txt" in str(exc_info.value)

    def test_case_insensitive(self, tmp_path):
        """Extension detection is case insensitive."""
        file_path = tmp_path / "script.PY"
        file_path.touch()
        assert detect_language_from_file(file_path) == ScriptLanguages.PYTHON


# =============================================================================
# Metadata Tests
# =============================================================================


class TestHasMcliMetadata:
    """Tests for has_mcli_metadata function."""

    def test_python_with_metadata(self):
        """Python file with metadata returns True."""
        content = """#!/usr/bin/env python3
# @description: Test command
# @version: 1.0.0

print("hello")
"""
        assert has_mcli_metadata(content, ScriptLanguages.PYTHON) is True

    def test_python_without_metadata(self):
        """Python file without metadata returns False."""
        content = """#!/usr/bin/env python3
# Just a comment
print("hello")
"""
        assert has_mcli_metadata(content, ScriptLanguages.PYTHON) is False

    def test_javascript_with_metadata(self):
        """JavaScript file with metadata returns True."""
        content = """#!/usr/bin/env bun
// @description: Test command
// @version: 1.0.0

console.log("hello");
"""
        assert has_mcli_metadata(content, ScriptLanguages.JAVASCRIPT) is True

    def test_javascript_without_metadata(self):
        """JavaScript file without metadata returns False."""
        content = """// Just a comment
console.log("hello");
"""
        assert has_mcli_metadata(content, ScriptLanguages.JAVASCRIPT) is False

    def test_notebook_with_metadata(self):
        """Notebook with mcli metadata returns True."""
        notebook = {"metadata": {"mcli": {"description": "test"}}, "cells": []}
        content = json.dumps(notebook)
        assert has_mcli_metadata(content, ScriptLanguages.IPYNB) is True

    def test_notebook_without_metadata(self):
        """Notebook without mcli metadata returns False."""
        notebook = {"metadata": {}, "cells": []}
        content = json.dumps(notebook)
        assert has_mcli_metadata(content, ScriptLanguages.IPYNB) is False

    def test_invalid_notebook_json(self):
        """Invalid JSON returns False."""
        content = "not valid json"
        assert has_mcli_metadata(content, ScriptLanguages.IPYNB) is False


class TestAddMetadataToScript:
    """Tests for add_metadata_to_script function."""

    def test_adds_metadata_after_shebang(self):
        """Metadata is added after shebang line."""
        content = """#!/usr/bin/env python3
print("hello")
"""
        result = add_metadata_to_script(
            content=content,
            language=ScriptLanguages.PYTHON,
            name="test",
            description="Test command",
            group="utils",
            version="1.0.0",
        )
        lines = result.split("\n")
        assert lines[0] == "#!/usr/bin/env python3"
        assert "@description: Test command" in result
        assert "@version: 1.0.0" in result
        assert "@group: utils" in result

    def test_adds_metadata_at_top_without_shebang(self):
        """Metadata is added at top if no shebang."""
        content = """print("hello")
"""
        result = add_metadata_to_script(
            content=content,
            language=ScriptLanguages.PYTHON,
            name="test",
            description="Test",
            group="utils",
        )
        assert result.startswith("# @description: Test")

    def test_javascript_uses_double_slash_comments(self):
        """JavaScript uses // for comments."""
        content = """console.log("hello");
"""
        result = add_metadata_to_script(
            content=content,
            language=ScriptLanguages.JAVASCRIPT,
            name="test",
            description="Test",
            group="utils",
        )
        assert "// @description: Test" in result

    def test_notebook_adds_to_json_metadata(self):
        """Notebook metadata is added to JSON structure."""
        notebook = {"metadata": {}, "cells": []}
        content = json.dumps(notebook)
        result = add_metadata_to_script(
            content=content,
            language=ScriptLanguages.IPYNB,
            name="test",
            description="Test notebook",
            group="data",
            version="2.0.0",
        )
        parsed = json.loads(result)
        assert parsed["metadata"]["mcli"]["description"] == "Test notebook"
        assert parsed["metadata"]["mcli"]["group"] == "data"
        assert parsed["metadata"]["mcli"]["version"] == "2.0.0"


# =============================================================================
# Template Generation Tests
# =============================================================================


class TestGetTemplate:
    """Tests for get_template function."""

    def test_python_template(self):
        """Generate Python template."""
        template = ScriptTemplate(
            name="mycommand",
            description="My command",
            group="utils",
            version="1.0.0",
            language=ScriptLanguages.PYTHON,
        )
        result = get_template(template)
        assert "#!/usr/bin/env python3" in result
        assert "@description: My command" in result
        assert "def mycommand_command" in result

    def test_shell_template(self):
        """Generate shell template."""
        template = ScriptTemplate(
            name="backup",
            description="Backup utility",
            group="utils",
            version="1.0.0",
            language=ScriptLanguages.SHELL,
            shell="bash",
        )
        result = get_template(template)
        assert "#!/usr/bin/env bash" in result
        assert "@description: Backup utility" in result
        assert "set -euo pipefail" in result

    def test_shell_template_with_zsh(self):
        """Generate zsh shell template."""
        template = ScriptTemplate(
            name="backup",
            description="Backup utility",
            group="utils",
            version="1.0.0",
            language=ScriptLanguages.SHELL,
            shell="zsh",
        )
        result = get_template(template)
        assert "#!/usr/bin/env zsh" in result

    def test_javascript_template(self):
        """Generate JavaScript template."""
        template = ScriptTemplate(
            name="fetch",
            description="Fetch data",
            group="api",
            version="1.0.0",
            language=ScriptLanguages.JAVASCRIPT,
        )
        result = get_template(template)
        assert "#!/usr/bin/env bun" in result
        assert "// @description: Fetch data" in result

    def test_typescript_template(self):
        """Generate TypeScript template."""
        template = ScriptTemplate(
            name="process",
            description="Process data",
            group="data",
            version="1.0.0",
            language=ScriptLanguages.TYPESCRIPT,
        )
        result = get_template(template)
        assert "#!/usr/bin/env bun" in result
        assert "const args: string[]" in result

    def test_notebook_template(self):
        """Generate Jupyter notebook template."""
        template = ScriptTemplate(
            name="analysis",
            description="Data analysis",
            group="ml",
            version="1.0.0",
            language=ScriptLanguages.IPYNB,
        )
        result = get_template(template)
        parsed = json.loads(result)
        assert parsed["metadata"]["mcli"]["description"] == "Data analysis"
        assert len(parsed["cells"]) == 3

    def test_unsupported_language_raises_error(self):
        """Unsupported language raises error."""
        template = ScriptTemplate(
            name="test",
            description="Test",
            group="utils",
            version="1.0.0",
            language="unsupported",
        )
        with pytest.raises(UnsupportedLanguageError):
            get_template(template)


# =============================================================================
# File Operations Tests
# =============================================================================


class TestSaveScript:
    """Tests for save_script function."""

    def test_saves_file_with_correct_extension(self, tmp_path):
        """File is saved with correct extension."""
        result = save_script(
            workflows_dir=tmp_path,
            name="mycommand",
            code="print('hello')",
            language=ScriptLanguages.PYTHON,
        )
        assert result == tmp_path / "mycommand.py"
        assert result.exists()

    def test_creates_directory_if_missing(self, tmp_path):
        """Creates workflows directory if it doesn't exist."""
        workflows_dir = tmp_path / "new_dir"
        result = save_script(
            workflows_dir=workflows_dir,
            name="cmd",
            code="echo hi",
            language=ScriptLanguages.SHELL,
        )
        assert workflows_dir.exists()
        assert result.exists()

    def test_python_script_is_executable(self, tmp_path):
        """Python scripts are made executable."""
        result = save_script(
            workflows_dir=tmp_path,
            name="cmd",
            code="#!/usr/bin/env python3\nprint('hi')",
            language=ScriptLanguages.PYTHON,
        )
        import stat

        assert result.stat().st_mode & stat.S_IXUSR

    def test_shell_script_is_executable(self, tmp_path):
        """Shell scripts are made executable."""
        result = save_script(
            workflows_dir=tmp_path,
            name="cmd",
            code="#!/bin/bash\necho hi",
            language=ScriptLanguages.SHELL,
        )
        import stat

        assert result.stat().st_mode & stat.S_IXUSR


class TestRestructureFileAsCommand:
    """Tests for restructure_file_as_command function."""

    def test_adds_metadata_to_file_without_it(self, tmp_path):
        """Adds metadata to file without existing metadata."""
        source_file = tmp_path / "script.py"
        source_file.write_text("print('hello')")

        result = restructure_file_as_command(
            file_path=source_file,
            name="test",
            description="Test command",
            group="utils",
            version="1.0.0",
            language=ScriptLanguages.PYTHON,
        )
        assert "@description: Test command" in result
        assert "print('hello')" in result

    def test_preserves_existing_metadata(self, tmp_path):
        """Preserves file content if metadata already exists."""
        original = """#!/usr/bin/env python3
# @description: Original description
# @version: 2.0.0

print('hello')
"""
        source_file = tmp_path / "script.py"
        source_file.write_text(original)

        result = restructure_file_as_command(
            file_path=source_file,
            name="test",
            description="New description",
            group="utils",
            version="1.0.0",
            language=ScriptLanguages.PYTHON,
        )
        assert "Original description" in result
        assert "New description" not in result


# =============================================================================
# Integration Tests
# =============================================================================


class TestExecuteNewCommand:
    """Integration tests for _execute_new_command function."""

    @patch("mcli.app.new_cmd.get_custom_commands_dir")
    @patch("mcli.app.new_cmd.ScriptLoader")
    @patch("mcli.app.new_cmd.is_git_repository")
    @patch("mcli.app.new_cmd.console")
    def test_creates_command_with_file_import(
        self, mock_console, mock_is_git, mock_loader, mock_get_dir, tmp_path
    ):
        """Successfully imports a file as a command."""
        mock_get_dir.return_value = tmp_path
        mock_is_git.return_value = False
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        # Create source file
        source_file = tmp_path / "source" / "backup.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("print('backup')")

        result = _execute_new_command(
            command_name=None,
            language=None,
            group="workflows",
            description="",
            cmd_version="1.0.0",
            template=False,
            shell=None,
            is_global=True,
            source_file=str(source_file),
        )

        assert result == EXIT_SUCCESS
        assert (tmp_path / "backup.py").exists()

    @patch("mcli.app.new_cmd.get_custom_commands_dir")
    @patch("mcli.app.new_cmd.ScriptLoader")
    @patch("mcli.app.new_cmd.is_git_repository")
    @patch("mcli.app.new_cmd.console")
    def test_creates_command_with_template_mode(
        self, mock_console, mock_is_git, mock_loader, mock_get_dir, tmp_path
    ):
        """Creates command using template mode."""
        mock_get_dir.return_value = tmp_path
        mock_is_git.return_value = False
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance

        result = _execute_new_command(
            command_name="mycommand",
            language="python",
            group="utils",
            description="My command",
            cmd_version="1.0.0",
            template=True,
            shell=None,
            is_global=True,
            source_file=None,
        )

        assert result == EXIT_SUCCESS
        created_file = tmp_path / "mycommand.py"
        assert created_file.exists()
        content = created_file.read_text()
        assert "@description: My command" in content

    def test_missing_command_name_returns_error(self):
        """Returns error when command name is missing."""
        result = _execute_new_command(
            command_name=None,
            language="python",
            group="workflows",
            description="",
            cmd_version="1.0.0",
            template=True,
            shell=None,
            is_global=True,
            source_file=None,
        )
        assert result == EXIT_ERROR

    def test_missing_language_returns_error(self):
        """Returns error when language is missing."""
        result = _execute_new_command(
            command_name="mycommand",
            language=None,
            group="workflows",
            description="",
            cmd_version="1.0.0",
            template=True,
            shell=None,
            is_global=True,
            source_file=None,
        )
        assert result == EXIT_ERROR

    def test_invalid_command_name_raises_error(self):
        """Invalid command name raises error."""
        with pytest.raises(InvalidCommandNameError):
            _execute_new_command(
                command_name="123invalid",
                language="python",
                group="workflows",
                description="",
                cmd_version="1.0.0",
                template=True,
                shell=None,
                is_global=True,
                source_file=None,
            )


# =============================================================================
# Constants Tests
# =============================================================================


class TestScriptConstants:
    """Tests for script-related constants."""

    def test_all_languages_have_extensions(self):
        """All languages have corresponding extensions."""
        for lang in ScriptLanguages.ALL:
            assert lang in ScriptExtensions.BY_LANGUAGE

    def test_all_extensions_map_to_languages(self):
        """All extensions map back to languages."""
        for ext in ScriptExtensions.ALL:
            assert ext in ScriptExtensions.TO_LANGUAGE

    def test_comment_prefixes_for_text_languages(self):
        """Text-based languages have comment prefixes."""
        text_languages = [
            ScriptLanguages.PYTHON,
            ScriptLanguages.SHELL,
            ScriptLanguages.JAVASCRIPT,
            ScriptLanguages.TYPESCRIPT,
        ]
        for lang in text_languages:
            assert lang in ScriptCommentPrefixes.BY_LANGUAGE

    def test_shell_types_all_list(self):
        """ShellTypes.ALL contains all shell types."""
        assert ShellTypes.BASH in ShellTypes.ALL
        assert ShellTypes.ZSH in ShellTypes.ALL
        assert ShellTypes.FISH in ShellTypes.ALL
        assert ShellTypes.SH in ShellTypes.ALL


# =============================================================================
# Error Tests
# =============================================================================


class TestErrorClasses:
    """Tests for custom error classes."""

    def test_invalid_command_name_error_message(self):
        """InvalidCommandNameError has informative message."""
        error = InvalidCommandNameError("bad@name")
        assert "bad@name" in str(error)
        assert "Invalid command name" in str(error)

    def test_invalid_group_name_error_message(self):
        """InvalidGroupNameError has informative message."""
        error = InvalidGroupNameError("123group")
        assert "123group" in str(error)
        assert "Invalid group name" in str(error)

    def test_unsupported_file_type_error_with_supported_list(self):
        """UnsupportedFileTypeError includes supported extensions."""
        error = UnsupportedFileTypeError(".xyz", [".py", ".sh"])
        assert ".xyz" in str(error)
        assert ".py" in str(error)
        assert ".sh" in str(error)

    def test_unsupported_language_error_with_supported_list(self):
        """UnsupportedLanguageError includes supported languages."""
        error = UnsupportedLanguageError("ruby", ["python", "shell"])
        assert "ruby" in str(error)
        assert "python" in str(error)
