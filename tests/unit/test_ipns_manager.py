"""Unit tests for src/mcli/lib/ipns_manager.py"""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mcli.lib.ipns_manager import (
    IPNSKeyInfo,
    build_pem_from_seed,
    derive_key_info,
    ensure_key_imported,
    get_repo_name,
    get_sync_key,
    publish_to_ipns,
    resolve_ipns,
)


# ---------------------------------------------------------------------------
# derive_key_info tests
# ---------------------------------------------------------------------------


def test_deterministic_same_inputs():
    """Same inputs produce identical key_name and seed."""
    a = derive_key_info("secret", "my-repo", "global")
    b = derive_key_info("secret", "my-repo", "global")
    assert a.key_name == b.key_name
    assert a.seed == b.seed


def test_different_keys_produce_different_output():
    """Different sync keys yield different results."""
    a = derive_key_info("key-one", "repo", "scope")
    b = derive_key_info("key-two", "repo", "scope")
    assert a.seed != b.seed
    assert a.key_name != b.key_name


def test_different_repos_produce_different_output():
    """Different repo names yield different results."""
    a = derive_key_info("key", "repo-a", "scope")
    b = derive_key_info("key", "repo-b", "scope")
    assert a.seed != b.seed
    assert a.key_name != b.key_name


def test_different_scopes_produce_different_output():
    """Different scopes yield different results."""
    a = derive_key_info("key", "repo", "global")
    b = derive_key_info("key", "repo", "team")
    assert a.seed != b.seed
    assert a.key_name != b.key_name


def test_key_name_format():
    """key_name starts with 'mcli-' followed by 16 hex characters."""
    info = derive_key_info("any-key", "any-repo", "any-scope")
    assert info.key_name.startswith("mcli-")
    suffix = info.key_name[len("mcli-"):]
    assert len(suffix) == 16
    assert all(c in "0123456789abcdef" for c in suffix)


def test_seed_is_32_bytes():
    """seed is exactly 32 bytes."""
    info = derive_key_info("key", "repo", "scope")
    assert len(info.seed) == 32
    assert isinstance(info.seed, bytes)


# ---------------------------------------------------------------------------
# build_pem_from_seed tests
# ---------------------------------------------------------------------------


def test_pem_format():
    """PEM output has proper header and footer."""
    seed = b"\x00" * 32
    pem = build_pem_from_seed(seed)
    assert "-----BEGIN PRIVATE KEY-----" in pem
    assert "-----END PRIVATE KEY-----" in pem


def test_pem_deterministic():
    """Same seed always produces the same PEM."""
    seed = b"\xde\xad\xbe\xef" * 8  # 32 bytes
    assert build_pem_from_seed(seed) == build_pem_from_seed(seed)


def test_pem_lines_wrapped_at_64():
    """Base64 content lines are at most 64 characters wide."""
    seed = bytes(range(32))
    pem = build_pem_from_seed(seed)
    lines = pem.strip().splitlines()
    # Strip header/footer
    body_lines = [l for l in lines if not l.startswith("-----")]
    assert all(len(l) <= 64 for l in body_lines)


# ---------------------------------------------------------------------------
# ensure_key_imported tests
# ---------------------------------------------------------------------------


def _make_key_list_response(keys):
    """Helper: build a mock response for /key/list."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"Keys": keys}
    return mock


def test_returns_existing_key_id():
    """When key already exists in Kubo, return its Id without importing."""
    info = IPNSKeyInfo(key_name="mcli-abc123", seed=b"\x00" * 32)
    existing_key = {"Name": "mcli-abc123", "Id": "k51q...existing"}
    list_resp = _make_key_list_response([existing_key])

    with patch("requests.post", return_value=list_resp) as mock_post:
        result = ensure_key_imported(info)

    assert result == "k51q...existing"
    # Only /key/list should be called — no /key/import
    assert mock_post.call_count == 1
    assert "key/list" in mock_post.call_args[0][0]


def test_imports_missing_key():
    """When key is missing, import it and return the new Id."""
    info = IPNSKeyInfo(key_name="mcli-newkey1", seed=b"\x01" * 32)

    list_resp = _make_key_list_response([])  # no keys
    import_resp = MagicMock()
    import_resp.status_code = 200
    import_resp.json.return_value = {"Id": "k51q...newkey"}

    with patch("requests.post", side_effect=[list_resp, import_resp]) as mock_post:
        result = ensure_key_imported(info)

    assert result == "k51q...newkey"
    assert mock_post.call_count == 2
    import_call_url = mock_post.call_args_list[1][0][0]
    assert "key/import" in import_call_url


def test_returns_none_on_api_error():
    """Connection errors return None."""
    info = IPNSKeyInfo(key_name="mcli-fail", seed=b"\x00" * 32)

    with patch("requests.post", side_effect=ConnectionError("refused")):
        result = ensure_key_imported(info)

    assert result is None


# ---------------------------------------------------------------------------
# get_sync_key tests
# ---------------------------------------------------------------------------


def test_reads_from_env():
    """MCLI_SYNC_KEY is returned from environment."""
    with patch.dict("os.environ", {"MCLI_SYNC_KEY": "test-secret-key"}):
        assert get_sync_key() == "test-secret-key"


def test_returns_none_when_unset():
    """Returns None when MCLI_SYNC_KEY is not set."""
    env_without_key = {k: v for k, v in __import__("os").environ.items() if k != "MCLI_SYNC_KEY"}
    with patch.dict("os.environ", env_without_key, clear=True):
        assert get_sync_key() is None


# ---------------------------------------------------------------------------
# get_repo_name tests
# ---------------------------------------------------------------------------


def _make_git_result(stdout: str, returncode: int = 0):
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.stdout = stdout
    mock.returncode = returncode
    return mock


def test_detects_git_remote():
    """Parses repo name from a git remote -v fetch line."""
    remote_output = "origin\thttps://github.com/user/my-repo.git (fetch)\n"
    mock_result = _make_git_result(remote_output)

    with patch("subprocess.run", return_value=mock_result):
        name = get_repo_name()

    assert name == "my-repo"


def test_falls_back_to_cwd():
    """Falls back to cwd name when git fails."""
    mock_result = _make_git_result("", returncode=128)

    with patch("subprocess.run", return_value=mock_result):
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = MagicMock(name="mock-cwd")
            mock_cwd.return_value.name = "my-cwd-project"
            name = get_repo_name()

    assert name == "my-cwd-project"


# ---------------------------------------------------------------------------
# publish_to_ipns / resolve_ipns tests (basic smoke tests via mocking)
# ---------------------------------------------------------------------------


def test_publish_to_ipns_returns_name():
    """publish_to_ipns returns the IPNS name on success."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Name": "k51q...ipnsname"}

    with patch("requests.post", return_value=mock_resp):
        result = publish_to_ipns("QmSomeCID", "mcli-abc123")

    assert result == "k51q...ipnsname"


def test_publish_to_ipns_returns_none_on_error():
    """publish_to_ipns returns None on connection error."""
    with patch("requests.post", side_effect=ConnectionError("refused")):
        result = publish_to_ipns("QmSomeCID", "mcli-abc123")

    assert result is None


def test_resolve_ipns_returns_cid():
    """resolve_ipns strips /ipfs/ prefix from resolved path."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Path": "/ipfs/QmResolvedCID"}

    with patch("requests.post", return_value=mock_resp):
        result = resolve_ipns("k51q...ipnsname")

    assert result == "QmResolvedCID"


def test_resolve_ipns_returns_none_on_error():
    """resolve_ipns returns None on connection error."""
    with patch("requests.post", side_effect=ConnectionError("refused")):
        result = resolve_ipns("k51q...ipnsname")

    assert result is None
