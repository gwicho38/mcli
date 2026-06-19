"""Tests for friendly runtime error surfacing of workflow scripts."""

import io

import click
import pytest
from click.testing import CliRunner
from rich.console import Console

from mcli.lib import workflow_runtime
from mcli.lib.workflow_runtime import render_script_error, wrap_command_invoke


@pytest.fixture
def captured_console(monkeypatch):
    """Redirect the module console into a buffer for assertions."""
    buf = io.StringIO()
    monkeypatch.setattr(workflow_runtime, "_console", Console(file=buf, width=200))
    return buf


def _crashing_command():
    @click.command(name="todos")
    def cmd():
        raise ValueError("boom from script")

    return cmd


def test_wrapped_command_renders_friendly_error_and_exits_1(captured_console, tmp_path):
    script = tmp_path / "todos.py"
    script.write_text("# fake\n")
    cmd = wrap_command_invoke(_crashing_command(), script)

    result = CliRunner().invoke(cmd)

    assert result.exit_code == 1
    out = captured_console.getvalue()
    assert "todos" in out
    assert "crashed" in out
    assert "ValueError" in out
    assert "boom from script" in out
    assert str(script) in out
    assert "github.com/gwicho38/mcli/issues" in out


def test_traceback_hidden_by_default(captured_console, tmp_path):
    cmd = wrap_command_invoke(_crashing_command(), tmp_path / "todos.py")
    CliRunner().invoke(cmd)
    out = captured_console.getvalue()
    assert "Traceback (most recent call last)" not in out


def test_traceback_shown_with_trace_env(captured_console, tmp_path, monkeypatch):
    monkeypatch.setenv("MCLI_TRACE_LEVEL", "1")
    cmd = wrap_command_invoke(_crashing_command(), tmp_path / "todos.py")
    CliRunner().invoke(cmd)
    out = captured_console.getvalue()
    assert "ValueError" in out
    # full traceback marker present when tracing enabled
    assert "Traceback" in out or "boom from script" in out


def test_click_exceptions_pass_through(captured_console, tmp_path):
    @click.command(name="needs_arg")
    @click.argument("name")
    def cmd(name):
        click.echo(name)

    wrapped = wrap_command_invoke(cmd, tmp_path / "needs_arg.py")
    # Missing required arg -> click UsageError, must NOT be swallowed as a crash
    result = CliRunner().invoke(wrapped)
    assert result.exit_code == 2  # click usage error
    assert "crashed" not in captured_console.getvalue()


def test_render_reports_deepest_script_line(captured_console, tmp_path):
    script = tmp_path / "todos.py"
    script.write_text("a\nb\nc\n")
    try:
        raise RuntimeError("kaboom")
    except RuntimeError as exc:
        render_script_error("todos", script, exc)
    out = captured_console.getvalue()
    assert "RuntimeError" in out
    assert str(script) in out
