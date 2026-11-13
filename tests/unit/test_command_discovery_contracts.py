"""Discover actual temporary Click modules and inspect their public command catalog."""

import importlib
import sys

import pytest

from mcli.lib.discovery.command_discovery import ClickCommandDiscovery

pytestmark = pytest.mark.unit


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    base = tmp_path / "catalog_fixture"
    commands = base / "commands" / "nested"
    commands.mkdir(parents=True)
    (base / "__init__.py").write_text("")
    (base / "commands" / "__init__.py").write_text("")
    (commands / "__init__.py").write_text("")
    (commands / "tools.py").write_text("""import click
@click.group(help="Manage backups")
def backups(): pass
@backups.group()
def remote(): pass
@remote.command(help="Upload encrypted backup")
def upload(): pass
@click.command(help="Print diagnostics")
def inspect_host(): pass
del remote, upload
""")
    (commands / "broken.py").write_text('raise ImportError("optional dependency absent")')
    (commands / "test_ignored.py").write_text('raise AssertionError("must not import")')
    (tmp_path / "config.toml").write_text('[paths]\nincluded_dirs=["commands/nested", "missing"]\n')
    importlib.invalidate_caches()
    yield ClickCommandDiscovery(base)
    for name in list(sys.modules):
        if name == "catalog_fixture" or name.startswith("catalog_fixture."):
            del sys.modules[name]


def test_nested_catalog_and_search_are_complete(catalog):
    discovered = catalog.discover_all_commands()
    names = {command.full_name for command in discovered}
    assert names == {
        "commands/nested.backups",
        "commands/nested.backups.remote",
        "commands/nested.backups.remote.upload",
        "commands/nested.inspect-host",
    }
    assert catalog.get_command_by_name("upload").group_name == "remote"
    assert (
        catalog.get_command_by_name("commands/nested.backups.remote.upload").description
        == "Upload encrypted backup"
    )
    assert catalog.get_command_by_name("absent") is None
    leaf = catalog.get_commands(include_groups=False)
    assert {c["name"] for c in leaf} == {"upload", "inspect-host"}
    assert catalog.search_commands("ENCRYPTED")[0]["name"] == "upload"
    assert len(catalog.search_commands("tools")) == 4
    assert catalog.search_commands("remote")[0]["name"] == "remote"
    assert catalog.search_commands("not-found") == []
    group = next(c for c in catalog.get_commands() if c["name"] == "backups")
    assert group["subcommands"] == ["remote"]
    assert all(c["is_active"] and c["language"] == "python" for c in leaf)
    assert {c.full_name for c in catalog.discover_all_commands()} == names
