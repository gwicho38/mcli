"""Manage only child process groups created by each isolated test."""

import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from mcli.workflow.daemon.process_manager import ProcessManager, ProcessStatus

pytestmark = pytest.mark.unit


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    manager = ProcessManager()
    yield manager
    for container in manager.containers.values():
        if container.process is not None and container.process.poll() is None:
            os.killpg(os.getpgid(container.process.pid), signal.SIGKILL)
            container.process.wait(timeout=5)


def ready(container, path):
    deadline = time.monotonic() + 5
    while not path.exists() and time.monotonic() < deadline:
        if not container.is_running():
            pytest.fail(container.get_logs())
        time.sleep(0.01)
    assert path.exists(), "owned child did not signal readiness"


def test_run_captures_output_and_uses_requested_environment(manager, tmp_path):
    script = 'import os,sys;print(os.environ["FIXTURE_VALUE"]);print(os.getcwd(),file=sys.stderr)'
    pid = manager.run(
        "fixture",
        sys.executable,
        ["-c", script],
        working_dir=str(tmp_path),
        environment={"FIXTURE_VALUE": "owned child"},
    )
    container = manager.containers[pid]
    container.process.wait(timeout=5)
    assert not container.is_running()
    assert manager.logs(pid)["stdout"] == "owned child\n"
    assert manager.logs(pid)["stderr"] == str(tmp_path) + "\n"
    assert manager.logs(pid, lines=2)["stdout"] == "owned child\n"
    detail = manager.inspect(pid)
    assert detail["name"] == "fixture" and detail["environment"] == {"FIXTURE_VALUE": "owned child"}
    assert detail["started_at"] is not None
    assert manager.stop(pid)
    assert manager.kill(pid)
    removed = manager.remove(pid)
    assert removed
    assert manager.inspect(pid) is None


@pytest.mark.parametrize("action", ["stop", "kill", "remove"])
def test_live_process_lifecycle_and_owned_group_cleanup(manager, tmp_path, action):
    marker = tmp_path / "ready"
    script = f'from pathlib import Path;import time;Path({str(marker)!r}).write_text("ready");time.sleep(30)'
    pid = manager.run("sleeper", sys.executable, ["-c", script])
    container = manager.containers[pid]
    ready(container, marker)
    assert manager.start(pid) is False
    assert manager.list_processes()[0]["name"] == "sleeper"
    assert manager.inspect(pid)["stats"]["num_threads"] >= 1
    assert getattr(manager, action)(pid)
    assert container.process.poll() is not None
    if action != "remove":
        assert container.info.status in {ProcessStatus.EXITED, ProcessStatus.KILLED}
        assert container.info.finished_at is not None
        assert manager.list_processes() == []
        assert len(manager.list_processes(all_processes=True)) == 1
        removed = manager.remove(pid)
        assert removed
    assert pid not in manager.containers


def test_stop_escalates_only_owned_process_that_ignores_sigterm(manager, tmp_path):
    marker = tmp_path / "ready"
    script = f'import signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path({str(marker)!r}).write_text("ready");time.sleep(30)'
    pid = manager.run("stubborn", sys.executable, ["-c", script])
    container = manager.containers[pid]
    ready(container, marker)
    assert manager.stop(pid, timeout=0.05)
    assert container.info.status is ProcessStatus.KILLED
    assert container.info.exit_code == -signal.SIGKILL


def test_missing_commands_and_unknown_ids_do_not_launch_processes(manager, tmp_path):
    for action in (manager.start, manager.stop, manager.kill, manager.remove):
        assert action("not-owned") is False
    assert manager.logs("not-owned") is None
    assert manager.inspect("not-owned") is None
    with pytest.raises(RuntimeError, match="Failed to start"):
        manager.run("missing", str(tmp_path / "does-not-exist"))
    assert manager.containers == {}


def test_created_containers_reload_and_corrupt_metadata_is_ignored(manager):
    pid = manager.create("pending", sys.executable, ["-c", "pass"])
    metadata = manager.base_dir / pid / "metadata.json"
    assert json.loads(metadata.read_text())["status"] == "created"
    corrupt = manager.base_dir / "corrupt"
    corrupt.mkdir()
    (corrupt / "metadata.json").write_text("invalid JSON")
    (manager.base_dir / "unrelated-file").write_text("ignored")
    reloaded = ProcessManager()
    assert set(reloaded.containers) == {pid}
    assert reloaded.inspect(pid)["status"] == "created"
    assert reloaded.inspect(pid)["args"] == ["-c", "pass"]
    assert reloaded.logs(pid) == {"stdout": "", "stderr": ""}


@pytest.mark.parametrize("status", list(ProcessStatus))
def test_known_legacy_status_records_are_preserved(manager, status):
    pid = manager.create("legacy", sys.executable, ["-c", "pass"])
    metadata = manager.base_dir / pid / "metadata.json"
    data = json.loads(metadata.read_text())
    data["status"] = "ProcessStatus." + status.name
    metadata.write_text(json.dumps(data))
    reloaded = ProcessManager()
    assert reloaded.containers[pid].info.status is status


@pytest.mark.parametrize(
    "status",
    ["ProcessStatus.UNKNOWN", "unknown", "OtherStatus.CREATED", "__import__('os').getpid()"],
)
def test_unknown_status_is_rejected_without_rewriting_metadata(manager, status):
    pid = manager.create("invalid", sys.executable, ["-c", "pass"])
    metadata = manager.base_dir / pid / "metadata.json"
    data = json.loads(metadata.read_text())
    data["status"] = status
    metadata.write_text(json.dumps(data))
    before = metadata.read_bytes()
    reloaded = ProcessManager()
    assert pid not in reloaded.containers
    assert metadata.read_bytes() == before
