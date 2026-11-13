from click.testing import CliRunner

from mcli.app.main import create_app


def test_main_app_help():
    runner = CliRunner()
    app = create_app()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "mcli" in result.output


def test_hello_command():
    runner = CliRunner()
    app = create_app()
    result = runner.invoke(app, ["self", "hello"])
    assert result.exit_code == 0
    assert "Hello" in result.output


def test_version_command():
    runner = CliRunner()
    app = create_app()
    result = runner.invoke(app, ["self", "version"])
    assert result.exit_code == 0
    assert "mcli version" in result.output


def test_version_verbose():
    runner = CliRunner()
    app = create_app()
    result = runner.invoke(app, ["self", "version", "--verbose"])
    assert result.exit_code == 0
    assert "mcli version" in result.output
    assert "Python:" in result.output


def test_lazy_command_loads_once_and_dispatches_real_options(monkeypatch):
    import sys
    from types import ModuleType

    import click

    from mcli.app.main import LazyCommand

    module = ModuleType("fixture_lazy_command")

    @click.command()
    @click.option("--count", type=int, default=1)
    @click.argument("name")
    def command(count, name):
        click.echo(name * count)

    module.command = command
    monkeypatch.setitem(sys.modules, module.__name__, module)
    lazy = LazyCommand("fixture", module.__name__ + ".command")
    assert lazy._loaded_command is None
    result = CliRunner().invoke(lazy, ["--count", "3", "a"])
    assert result.exit_code == 0 and result.output == "aaa\n"
    assert lazy._loaded_command is command
    monkeypatch.delitem(sys.modules, module.__name__)
    result = CliRunner().invoke(lazy, ["b"])
    assert result.exit_code == 0 and result.output == "b\n"


def test_lazy_group_dispatch_and_completion_aware_static_catalog(monkeypatch):
    import sys
    from types import ModuleType

    import click

    from mcli.app.completion_helpers import create_completion_aware_lazy_group, get_completion_items
    from mcli.app.main import LazyGroup

    module = ModuleType("fixture_lazy_group")

    @click.group()
    @click.option("--prefix", default="")
    @click.pass_context
    def group(ctx, prefix):
        ctx.obj = prefix

    @group.command()
    @click.pass_context
    def hello(ctx):
        click.echo(ctx.obj + "hello")

    module.group = group
    monkeypatch.setitem(sys.modules, module.__name__, module)
    lazy = LazyGroup("fixture", module.__name__ + ".group")
    result = CliRunner().invoke(lazy, ["--prefix", "test-", "hello"])
    assert result.exit_code == 0 and result.output == "test-hello\n"
    assert lazy.list_commands(click.Context(lazy)) == ["hello"]
    completion = create_completion_aware_lazy_group("model", "absent.module.group")
    assert "download" in completion.list_commands(click.Context(completion))
    assert completion._loaded_group is None
    values = [
        x.value for x in get_completion_items(["workflow", "politician-trading", "run"], "--us")
    ]
    assert values == ["--us-only"]
    assert get_completion_items(["missing"]) == []
    dynamic = create_completion_aware_lazy_group("fixture", module.__name__ + ".group")
    assert dynamic.list_commands(click.Context(dynamic)) == ["hello"]
    assert [x.value for x in dynamic.shell_complete(click.Context(dynamic), "he")] == ["hello"]
    result = CliRunner().invoke(dynamic, ["hello"])
    assert result.exit_code == 0 and result.output == "hello\n"


def test_module_discovery_respects_explicit_config_and_excludes_resources(tmp_path, monkeypatch):
    from mcli.app.main import discover_modules

    monkeypatch.chdir(tmp_path)
    base = tmp_path / "mcli"
    for relative in [
        "app/direct.py",
        "app/nested/tool.py",
        "app/resources/ignored.py",
        "app/__init__.py",
        "workflow/workflow.py",
        "workflow/daemon/ignored.py",
        "self/version.py",
    ]:
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pass\n")
    config = tmp_path / "scan.toml"
    config.write_text('[paths]\nincluded_dirs=["app/nested","workflow","absent"]\n')
    assert set(discover_modules(base, config)) == {"mcli.app.nested.tool", "mcli.workflow.workflow"}
    config.write_text("invalid toml [")
    assert set(discover_modules(base, config)) == {
        "mcli.app.direct",
        "mcli.app.nested.tool",
        "mcli.workflow.workflow",
        "mcli.self.version",
    }
    (tmp_path / "config.toml").write_text('[paths]\nincluded_dirs=["self"]\n')
    assert discover_modules(base) == ["mcli.self.version"]
