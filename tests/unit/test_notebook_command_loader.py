"""
Unit tests for NotebookCommandLoader.

Tests the extraction of Click commands from Jupyter notebook cells.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import click
import pytest

from mcli.workflow.notebook.command_loader import NotebookCommandLoader
from mcli.workflow.notebook.schema import (
    CellType,
    MCLIMetadata,
    NotebookCell,
    NotebookMetadata,
    WorkflowNotebook,
)


@pytest.fixture
def sample_notebook():
    """Create a sample notebook with commands."""
    cells = [
        NotebookCell(
            cell_type=CellType.MARKDOWN,
            source=["# Test Commands\n", "This is a test notebook."],
        ),
        NotebookCell(
            cell_type=CellType.CODE,
            source=["import click\n"],
        ),
        NotebookCell(
            cell_type=CellType.CODE,
            source=[
                "@click.command()\n",
                "@click.option('--name', default='World')\n",
                "def hello(name):\n",
                '    """Say hello"""\n',
                '    click.echo(f"Hello, {name}!")\n',
            ],
        ),
        NotebookCell(
            cell_type=CellType.CODE,
            source=[
                "@click.command()\n",
                "@click.argument('x', type=int)\n",
                "@click.argument('y', type=int)\n",
                "def add(x, y):\n",
                '    """Add two numbers"""\n',
                "    click.echo(f'{x} + {y} = {x + y}')\n",
            ],
        ),
    ]

    metadata = NotebookMetadata(
        mcli=MCLIMetadata(
            name="test",
            description="Test notebook",
            version="1.0.0",
            language="python",
        )
    )

    return WorkflowNotebook(cells=cells, metadata=metadata)


@pytest.fixture
def notebook_without_commands():
    """Create a notebook without any commands."""
    cells = [
        NotebookCell(
            cell_type=CellType.CODE,
            source=["import click\n"],
        ),
        NotebookCell(
            cell_type=CellType.CODE,
            source=["def helper():\n", "    return 42\n"],
        ),
    ]

    metadata = NotebookMetadata(
        mcli=MCLIMetadata(
            name="no_commands",
            description="Notebook without commands",
            version="1.0.0",
            language="python",
        )
    )

    return WorkflowNotebook(cells=cells, metadata=metadata)


class TestNotebookCommandLoader:
    """Test NotebookCommandLoader class."""

    def test_is_command_cell_with_click_command(self):
        """Test detection of @click.command() decorator."""
        loader = NotebookCommandLoader(Mock())
        source = "@click.command()\ndef test():\n    pass"
        assert loader._is_command_cell(source) is True

    def test_is_command_cell_with_click_group(self):
        """Test detection of @click.group() decorator."""
        loader = NotebookCommandLoader(Mock())
        source = "@click.group()\ndef test():\n    pass"
        assert loader._is_command_cell(source) is True

    def test_is_command_cell_with_command_shorthand(self):
        """Test detection of @command() decorator."""
        loader = NotebookCommandLoader(Mock())
        source = "@command()\ndef test():\n    pass"
        assert loader._is_command_cell(source) is True

    def test_is_command_cell_without_decorator(self):
        """Test non-command cell is not detected."""
        loader = NotebookCommandLoader(Mock())
        source = "def test():\n    pass"
        assert loader._is_command_cell(source) is False

    def test_extract_function_name(self):
        """Test extraction of function name from command cell."""
        loader = NotebookCommandLoader(Mock())
        source = "@click.command()\ndef my_command():\n    pass"
        assert loader._extract_function_name(source) == "my_command"

    def test_extract_function_name_with_multiple_decorators(self):
        """Test extraction with multiple decorators."""
        loader = NotebookCommandLoader(Mock())
        source = (
            "@click.command()\n" "@click.option('--flag')\n" "def my_command(flag):\n" "    pass"
        )
        assert loader._extract_function_name(source) == "my_command"

    def test_extract_function_name_no_decorator(self):
        """Test extraction returns None for non-command function."""
        loader = NotebookCommandLoader(Mock())
        source = "def helper():\n    pass"
        assert loader._extract_function_name(source) is None

    def test_extract_function_name_invalid_syntax(self):
        """Test extraction handles syntax errors gracefully."""
        loader = NotebookCommandLoader(Mock())
        source = "@click.command(\ndef invalid syntax"
        assert loader._extract_function_name(source) is None

    def test_execute_setup_cells(self, sample_notebook):
        """Test that setup cells are executed."""
        loader = NotebookCommandLoader(sample_notebook)
        loader._execute_setup_cells()

        # Check that click was imported
        assert "click" in loader.globals_dict
        assert loader.globals_dict["click"] == click

    def test_load_command_from_cell(self, sample_notebook):
        """Test loading a command from a cell."""
        loader = NotebookCommandLoader(sample_notebook)
        loader._execute_setup_cells()

        # Get the hello command cell
        hello_cell = sample_notebook.cells[2]
        cmd = loader._load_command_from_cell(hello_cell.source_text)

        assert cmd is not None
        assert isinstance(cmd, click.Command)
        assert cmd.name == "hello"

    def test_extract_commands(self, sample_notebook):
        """Test extraction of all commands from notebook."""
        loader = NotebookCommandLoader(sample_notebook)
        commands = loader.extract_commands()

        assert len(commands) == 2
        assert commands[0][0] == "hello"
        assert commands[1][0] == "add"
        assert all(isinstance(cmd[1], click.Command) for cmd in commands)

    def test_extract_commands_empty_notebook(self, notebook_without_commands):
        """Test extraction from notebook with no commands."""
        loader = NotebookCommandLoader(notebook_without_commands)
        commands = loader.extract_commands()

        assert len(commands) == 0

    def test_create_group(self, sample_notebook):
        """Test creation of Click group from notebook."""
        loader = NotebookCommandLoader(sample_notebook)
        group = loader.create_group()

        assert group is not None
        assert isinstance(group, click.Group)
        assert group.name == "test"
        assert "hello" in group.commands
        assert "add" in group.commands

    def test_create_group_custom_name(self, sample_notebook):
        """Test group creation with custom name."""
        loader = NotebookCommandLoader(sample_notebook)
        group = loader.create_group(group_name="custom")

        assert group.name == "custom"

    def test_create_group_with_description(self, sample_notebook):
        """Test that group inherits notebook description."""
        loader = NotebookCommandLoader(sample_notebook)
        group = loader.create_group()

        assert group.__doc__ == "Test notebook"

    def test_create_group_no_commands(self, notebook_without_commands):
        """Test that create_group returns None when no commands found."""
        loader = NotebookCommandLoader(notebook_without_commands)
        group = loader.create_group()

        assert group is None

    @patch("mcli.workflow.notebook.command_loader.WorkflowConverter")
    def test_from_file(self, mock_converter, sample_notebook):
        """Test creation of loader from file."""
        mock_converter.load_notebook_json.return_value = sample_notebook
        notebook_path = Path("/tmp/test.ipynb")

        loader = NotebookCommandLoader.from_file(notebook_path)

        assert loader is not None
        assert loader.notebook == sample_notebook
        mock_converter.load_notebook_json.assert_called_once_with(notebook_path)

    @patch("mcli.workflow.notebook.command_loader.WorkflowConverter")
    def test_load_group_from_file(self, mock_converter, sample_notebook):
        """Test loading group directly from file."""
        mock_converter.load_notebook_json.return_value = sample_notebook
        notebook_path = Path("/tmp/test.ipynb")

        group = NotebookCommandLoader.load_group_from_file(notebook_path)

        assert group is not None
        assert isinstance(group, click.Group)
        assert group.name == "test"
        assert len(group.commands) == 2


class TestCommandExecution:
    """Test that loaded commands execute correctly."""

    def test_hello_command_execution(self, sample_notebook):
        """Test that the hello command executes correctly."""
        loader = NotebookCommandLoader(sample_notebook)
        group = loader.create_group()

        # Invoke the hello command
        runner = click.testing.CliRunner()
        result = runner.invoke(group, ["hello", "--name", "Claude"])

        assert result.exit_code == 0
        assert "Hello, Claude!" in result.output

    def test_add_command_execution(self, sample_notebook):
        """Test that the add command executes correctly."""
        loader = NotebookCommandLoader(sample_notebook)
        group = loader.create_group()

        # Invoke the add command
        runner = click.testing.CliRunner()
        result = runner.invoke(group, ["add", "5", "3"])

        assert result.exit_code == 0
        assert "5 + 3 = 8" in result.output

    def test_command_with_default_option(self, sample_notebook):
        """Test command with default option value."""
        loader = NotebookCommandLoader(sample_notebook)
        group = loader.create_group()

        # Invoke hello without --name (should use default "World")
        runner = click.testing.CliRunner()
        result = runner.invoke(group, ["hello"])

        assert result.exit_code == 0
        assert "Hello, World!" in result.output


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_cell_with_syntax_error(self):
        """Test handling of cell with syntax error."""
        cells = [
            NotebookCell(
                cell_type=CellType.CODE,
                source=["import click\n"],
            ),
            NotebookCell(
                cell_type=CellType.CODE,
                source=[
                    "@click.command(\n",  # Missing closing parenthesis
                    "def broken():\n",
                    "    pass\n",
                ],
            ),
        ]

        metadata = NotebookMetadata(
            mcli=MCLIMetadata(
                name="broken",
                description="Broken notebook",
                version="1.0.0",
                language="python",
            )
        )

        notebook = WorkflowNotebook(cells=cells, metadata=metadata)
        loader = NotebookCommandLoader(notebook)
        commands = loader.extract_commands()

        # Should handle error gracefully and return empty list
        assert len(commands) == 0

    def test_notebook_with_only_markdown(self):
        """Test notebook with only markdown cells."""
        cells = [
            NotebookCell(
                cell_type=CellType.MARKDOWN,
                source=["# Title\n"],
            ),
            NotebookCell(
                cell_type=CellType.MARKDOWN,
                source=["Some text\n"],
            ),
        ]

        metadata = NotebookMetadata(
            mcli=MCLIMetadata(
                name="markdown_only",
                description="Markdown only",
                version="1.0.0",
                language="python",
            )
        )

        notebook = WorkflowNotebook(cells=cells, metadata=metadata)
        loader = NotebookCommandLoader(notebook)
        commands = loader.extract_commands()

        assert len(commands) == 0

    def test_function_without_click_decorator(self):
        """Test that regular functions are not extracted as commands."""
        cells = [
            NotebookCell(
                cell_type=CellType.CODE,
                source=["import click\n"],
            ),
            NotebookCell(
                cell_type=CellType.CODE,
                source=[
                    "def helper(x):\n",
                    "    return x * 2\n",
                ],
            ),
        ]

        metadata = NotebookMetadata(
            mcli=MCLIMetadata(
                name="helpers",
                description="Helper functions",
                version="1.0.0",
                language="python",
            )
        )

        notebook = WorkflowNotebook(cells=cells, metadata=metadata)
        loader = NotebookCommandLoader(notebook)
        commands = loader.extract_commands()

        assert len(commands) == 0


class TestCompletionModeStdoutSuppression:
    """Test that stdout is suppressed during shell completion mode.

    When tab completion is running, any stdout output from executed cells
    (like print statements) corrupts the completion response. This tests
    that stdout is properly suppressed during completion mode.
    """

    @pytest.fixture
    def notebook_with_print_statements(self):
        """Create a notebook with cells that print to stdout."""
        cells = [
            NotebookCell(
                cell_type=CellType.CODE,
                source=["import click\n"],
            ),
            NotebookCell(
                cell_type=CellType.CODE,
                source=[
                    "# Setup cell with print statement\n",
                    "for i in range(5):\n",
                    "    print(i)\n",
                ],
            ),
            NotebookCell(
                cell_type=CellType.CODE,
                source=[
                    "print('hello from setup')\n",
                ],
            ),
            NotebookCell(
                cell_type=CellType.CODE,
                source=[
                    "@click.command()\n",
                    "def my_command():\n",
                    '    """Test command"""\n',
                    "    click.echo('command executed')\n",
                ],
            ),
        ]

        metadata = NotebookMetadata(
            mcli=MCLIMetadata(
                name="print_test",
                description="Notebook with print statements",
                version="1.0.0",
                language="python",
            )
        )

        return WorkflowNotebook(cells=cells, metadata=metadata)

    def test_stdout_suppressed_during_completion(self, notebook_with_print_statements, capsys):
        """Test that print statements in setup cells don't pollute stdout during completion."""
        import os

        from mcli.lib.constants import EnvVars

        # Set completion mode environment variable
        os.environ[EnvVars.COMPLETE] = "zsh_complete"

        try:
            loader = NotebookCommandLoader(notebook_with_print_statements)
            commands = loader.extract_commands()

            # Capture what was printed
            captured = capsys.readouterr()

            # During completion mode, stdout should be empty (no print pollution)
            assert (
                captured.out == ""
            ), f"Expected no stdout during completion mode, but got: {captured.out!r}"

            # Commands should still be extracted successfully
            assert len(commands) == 1
            assert commands[0][0] == "my_command"
        finally:
            # Clean up environment
            del os.environ[EnvVars.COMPLETE]

    def test_stdout_suppressed_during_loading(self, notebook_with_print_statements, capsys):
        """Test that print statements are suppressed during command loading.

        Output should be suppressed during loading to prevent log spam when
        listing or discovering commands (e.g., `mcli run`).
        """
        import os

        from mcli.lib.constants import EnvVars

        # Ensure we're NOT in completion mode and NOT in execution mode
        if EnvVars.COMPLETE in os.environ:
            del os.environ[EnvVars.COMPLETE]
        if EnvVars.MCLI_NOTEBOOK_EXECUTE in os.environ:
            del os.environ[EnvVars.MCLI_NOTEBOOK_EXECUTE]

        loader = NotebookCommandLoader(notebook_with_print_statements)
        commands = loader.extract_commands()

        # Capture what was printed
        captured = capsys.readouterr()

        # During loading, stdout should be suppressed (no print pollution)
        assert captured.out == "", f"Expected no stdout during loading, but got: {captured.out!r}"

        # Commands should still be extracted successfully
        assert len(commands) == 1
        assert commands[0][0] == "my_command"

    def test_stdout_not_suppressed_during_execution(self, notebook_with_print_statements, capsys):
        """Test that print statements work during command execution mode.

        When MCLI_NOTEBOOK_EXECUTE=1, output should NOT be suppressed because
        the user is actually running a command and wants to see output.
        """
        import os

        from mcli.lib.constants import EnvVars

        # Set execution mode
        os.environ[EnvVars.MCLI_NOTEBOOK_EXECUTE] = "1"

        # Ensure we're NOT in completion mode
        if EnvVars.COMPLETE in os.environ:
            del os.environ[EnvVars.COMPLETE]

        try:
            loader = NotebookCommandLoader(notebook_with_print_statements)
            commands = loader.extract_commands()

            # Capture what was printed
            captured = capsys.readouterr()

            # During execution mode, print statements should appear
            assert "0" in captured.out
            assert "1" in captured.out
            assert "hello from setup" in captured.out

            # Commands should still be extracted successfully
            assert len(commands) == 1
            assert commands[0][0] == "my_command"
        finally:
            # Clean up environment
            del os.environ[EnvVars.MCLI_NOTEBOOK_EXECUTE]
