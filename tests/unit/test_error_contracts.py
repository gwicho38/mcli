"""Errors expose actionable CLI diagnostics and retain machine-readable context."""

from pathlib import Path

import pytest

from mcli.lib import errors

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "error,category,context,expected",
    [
        (
            errors.InvalidCommandNameError("Bad-Name"),
            errors.CommandError,
            {"name": "Bad-Name"},
            "lowercase",
        ),
        (
            errors.InvalidCommandNameError("Bad", "reserved name"),
            errors.CommandError,
            {"name": "Bad"},
            "reserved name",
        ),
        (
            errors.CommandNotFoundError("backup", ["local", "global"]),
            errors.CommandError,
            {"searched_locations": ["local", "global"]},
            "local, global",
        ),
        (
            errors.CommandNotFoundError("backup"),
            errors.CommandError,
            {"searched_locations": []},
            "backup",
        ),
        (
            errors.CommandAlreadyExistsError("backup", Path("workflows/backup.py")),
            errors.CommandError,
            {"existing_path": Path("workflows/backup.py")},
            "workflows/backup.py",
        ),
        (
            errors.UnsupportedLanguageError("unknown", ["python", "shell"]),
            errors.ScriptError,
            {"language": "unknown"},
            "python, shell",
        ),
        (
            errors.UnsupportedFileTypeError(".bin", [".py", ".sh"]),
            errors.ScriptError,
            {"extension": ".bin"},
            ".py, .sh",
        ),
        (
            errors.InvalidScriptError("workflow.py", "invalid encoding"),
            errors.ScriptError,
            {"path": Path("workflow.py")},
            "invalid encoding",
        ),
        (
            errors.ScriptParseError("workflow.py", 7, "unexpected token"),
            errors.ScriptError,
            {"line_number": 7},
            "Line 7: unexpected token",
        ),
        (
            errors.ScriptParseError("workflow.py"),
            errors.ScriptError,
            {"line_number": None},
            "workflow.py",
        ),
        (
            errors.MetadataExtractionError("workflow.py", "unterminated metadata"),
            errors.ScriptError,
            {"path": Path("workflow.py")},
            "unterminated metadata",
        ),
        (errors.InvalidGroupNameError("BAD"), errors.ValidationError, {"name": "BAD"}, "lowercase"),
        (
            errors.InvalidFilePathError("absent.py", "not found"),
            errors.ValidationError,
            {"path": Path("absent.py")},
            "not found",
        ),
        (
            errors.MissingConfigurationError("endpoint", "config.toml"),
            errors.ConfigurationError,
            {"key": "endpoint", "config_file": "config.toml"},
            "config.toml",
        ),
        (
            errors.MissingConfigurationError("endpoint"),
            errors.ConfigurationError,
            {"key": "endpoint", "config_file": None},
            "endpoint",
        ),
    ],
)
def test_errors_keep_context_and_actionable_details(error, category, context, expected):
    assert isinstance(error, category) and isinstance(error, errors.McliError)
    assert expected in str(error)
    assert all(getattr(error, key) == value for key, value in context.items())
    assert error.args == (str(error),)


def test_execution_error_preserves_exit_status_and_bounds_displayed_stderr():
    diagnostic = "x" * 201 + "sensitive-tail"
    error = errors.CommandExecutionError("backup", exit_code=17, stderr=diagnostic)
    assert error.exit_code == 17 and error.stderr == diagnostic
    assert "Exit code: 17" in str(error)
    assert "x" * 200 in str(error)
    assert "sensitive-tail" not in str(error)
    assert "Details" not in str(errors.CommandExecutionError("backup"))
    assert (
        str(errors.McliError("invalid", "retry with config"))
        == "invalid\n  Details: retry with config"
    )
