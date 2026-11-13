"""Exercise encryption from the published wheel without development dependencies."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.slow
def test_default_wheel_supports_encrypted_storage(tmp_path):
    """A default installation must supply the crypto backend used by storage."""
    uv = shutil.which("uv")
    assert uv is not None, "The project's UV package manager must be installed"
    root = Path(__file__).resolve().parents[2]
    wheel_dir = tmp_path / "dist"
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    environment.pop("PYTHONPATH", None)

    def run(*args):
        result = subprocess.run(
            args, cwd=tmp_path, env=environment, text=True, capture_output=True, timeout=180
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    run(uv, "build", "--wheel", "--out-dir", str(wheel_dir), str(root))
    runtime = tmp_path / "runtime"
    run(uv, "venv", "--python", sys.executable, str(runtime))
    python = runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run(uv, "pip", "install", "--python", str(python), str(next(wheel_dir.glob("*.whl"))))
    run(
        str(python),
        "-I",
        "-c",
        "from mcli.storage.encryption import encrypt_data, decrypt_data; "
        "payload = bytes(range(256)); key = 'temporary packaging regression key'; "
        "encrypted = encrypt_data(payload, key); "
        "assert encrypted != payload; "
        "assert decrypt_data(encrypted, key) == payload; "
        "from mcli.lib.api.api import ClickToAPIDecorator; "
        "from fastapi.testclient import TestClient; "
        "client = TestClient(ClickToAPIDecorator()._create_fastapi_app()); "
        "response = client.get('/health'); "
        "assert response.status_code == 200; "
        "assert response.json()['status'] == 'healthy'; "
        "from mcli.lib.secrets.manager import SecretsManager; "
        "from importlib.util import find_spec; assert find_spec('pytest') is None",
    )
