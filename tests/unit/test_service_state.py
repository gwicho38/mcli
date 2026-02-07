"""Tests for service state persistence."""

import json

import pytest

from mcli.lib.services.state import ServiceState, list_states, load_state, remove_state, save_state


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Override services state directory to a temp location."""
    state_path = tmp_path / "state"
    state_path.mkdir()
    monkeypatch.setattr(
        "mcli.lib.services.state.get_services_state_dir",
        lambda: state_path,
    )
    return state_path


class TestServiceState:
    def test_defaults(self):
        state = ServiceState(name="test")
        assert state.name == "test"
        assert state.status == "stopped"
        assert state.pid is None
        assert state.restart_count == 0

    def test_save_and_load(self, state_dir):
        state = ServiceState(
            name="my-svc",
            status="running",
            pid=12345,
            started_at="2026-01-01T00:00:00",
        )
        assert save_state(state) is True

        loaded = load_state("my-svc")
        assert loaded is not None
        assert loaded.name == "my-svc"
        assert loaded.status == "running"
        assert loaded.pid == 12345
        assert loaded.started_at == "2026-01-01T00:00:00"

    def test_load_missing(self, state_dir):
        result = load_state("nonexistent")
        assert result is None

    def test_remove(self, state_dir):
        state = ServiceState(name="to-remove")
        save_state(state)
        assert (state_dir / "to-remove.json").exists()

        assert remove_state("to-remove") is True
        assert not (state_dir / "to-remove.json").exists()

    def test_remove_nonexistent(self, state_dir):
        assert remove_state("nope") is True

    def test_list_states(self, state_dir):
        save_state(ServiceState(name="alpha"))
        save_state(ServiceState(name="beta"))
        save_state(ServiceState(name="gamma"))

        states = list_states()
        names = [s.name for s in states]
        assert "alpha" in names
        assert "beta" in names
        assert "gamma" in names

    def test_list_states_empty(self, state_dir):
        assert list_states() == []

    def test_json_roundtrip(self, state_dir):
        state = ServiceState(
            name="rt",
            status="running",
            pid=999,
            restart_count=3,
            config={"port": 8080, "command": "python app.py"},
        )
        save_state(state)

        raw = json.loads((state_dir / "rt.json").read_text())
        assert raw["name"] == "rt"
        assert raw["pid"] == 999
        assert raw["config"]["port"] == 8080

    def test_load_corrupt_file(self, state_dir):
        (state_dir / "bad.json").write_text("not json")
        result = load_state("bad")
        assert result is None
