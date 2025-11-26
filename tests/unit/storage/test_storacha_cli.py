"""Unit tests for Storacha CLI wrapper."""

import json
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcli.storage.storacha_cli import BridgeTokens, StorachaCLI


@pytest.fixture
def temp_config_path():
    """Create a temporary config file path."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        yield Path(f.name)


@pytest.fixture
def cli(temp_config_path):
    """Create a StorachaCLI instance with temporary config."""
    return StorachaCLI(config_path=temp_config_path)


class TestBridgeTokens:
    """Tests for BridgeTokens dataclass."""

    def test_is_expired_no_expiration(self):
        """Test that tokens without expiration are not expired."""
        tokens = BridgeTokens(
            x_auth_secret="secret",
            authorization="auth",
            agent_did="did:key:test",
            space_did="did:key:space",
            capabilities=["store/add"],
            expires_at=None,
        )
        assert not tokens.is_expired()

    def test_is_expired_future(self):
        """Test that future expiration is not expired."""
        tokens = BridgeTokens(
            x_auth_secret="secret",
            authorization="auth",
            agent_did="did:key:test",
            space_did="did:key:space",
            capabilities=["store/add"],
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        assert not tokens.is_expired()

    def test_is_expired_past(self):
        """Test that past expiration is expired."""
        tokens = BridgeTokens(
            x_auth_secret="secret",
            authorization="auth",
            agent_did="did:key:test",
            space_did="did:key:space",
            capabilities=["store/add"],
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert tokens.is_expired()

    def test_to_headers(self):
        """Test that to_headers returns correct dict."""
        tokens = BridgeTokens(
            x_auth_secret="my-secret",
            authorization="my-auth",
            agent_did="did:key:test",
            space_did="did:key:space",
            capabilities=[],
        )
        headers = tokens.to_headers()
        assert headers["X-Auth-Secret"] == "my-secret"
        assert headers["Authorization"] == "my-auth"


class TestStorachaCLIInit:
    """Tests for StorachaCLI initialization."""

    def test_loads_existing_config(self, temp_config_path):
        """Test that existing config is loaded."""
        config = {"email": "test@example.com", "agent_did": "did:key:test"}
        temp_config_path.write_text(json.dumps(config))

        cli = StorachaCLI(config_path=temp_config_path)
        assert cli.config["email"] == "test@example.com"

    def test_creates_default_config(self, temp_config_path):
        """Test that missing config creates empty dict."""
        temp_config_path.unlink()  # Remove the file
        cli = StorachaCLI(config_path=temp_config_path)
        assert cli.config == {}

    def test_creates_parent_directory(self, tmp_path):
        """Test that parent directory is created if missing."""
        config_path = tmp_path / "subdir" / "config.json"
        cli = StorachaCLI(config_path=config_path)
        assert config_path.parent.exists()


class TestStorachaCLIStatus:
    """Tests for CLI status methods."""

    def test_is_cli_installed_true(self, cli):
        """Test is_cli_installed when CLI is available."""
        with patch("shutil.which", return_value="/usr/bin/storacha"):
            assert cli.is_cli_installed() is True

    def test_is_cli_installed_false(self, cli):
        """Test is_cli_installed when CLI is not available."""
        with patch("shutil.which", return_value=None):
            assert cli.is_cli_installed() is False

    def test_get_agent_did_from_cli(self, cli):
        """Test get_agent_did retrieves DID from CLI."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "did:key:z6MkTestDID123"

        with patch.object(cli, "_run_cli", return_value=mock_result):
            did = cli.get_agent_did()
            assert did == "did:key:z6MkTestDID123"

    def test_get_agent_did_from_config(self, cli):
        """Test get_agent_did falls back to config."""
        cli.config["agent_did"] = "did:key:cached"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch.object(cli, "_run_cli", return_value=mock_result):
            did = cli.get_agent_did()
            assert did == "did:key:cached"

    def test_is_authenticated_true(self, cli):
        """Test is_authenticated when accounts exist."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "account1@example.com"
        mock_result.stderr = ""

        with patch.object(cli, "_run_cli", return_value=mock_result):
            assert cli.is_authenticated() is True

    def test_is_authenticated_false(self, cli):
        """Test is_authenticated when not authorized."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Agent has not been authorized"

        with patch.object(cli, "_run_cli", return_value=mock_result):
            assert cli.is_authenticated() is False


class TestStorachaCLISpaces:
    """Tests for space management methods."""

    def test_list_spaces(self, cli):
        """Test list_spaces parses CLI output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "* did:key:space1\n  did:key:space2"

        with patch.object(cli, "_run_cli", return_value=mock_result):
            spaces = cli.list_spaces()
            assert len(spaces) == 2
            assert "did:key:space1" in spaces
            assert "did:key:space2" in spaces

    def test_list_spaces_empty(self, cli):
        """Test list_spaces with no spaces."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch.object(cli, "_run_cli", return_value=mock_result):
            spaces = cli.list_spaces()
            assert spaces == []

    def test_create_space(self, cli):
        """Test create_space creates and returns DID."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "did:key:newspace123"
        mock_result.stderr = ""

        with patch.object(cli, "_run_cli", return_value=mock_result):
            space_did = cli.create_space("test-space")
            assert space_did == "did:key:newspace123"
            assert cli.config["space_did"] == "did:key:newspace123"

    def test_select_space(self, cli):
        """Test select_space updates config."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(cli, "_run_cli", return_value=mock_result):
            result = cli.select_space("did:key:myspace")
            assert result is True
            assert cli.config["space_did"] == "did:key:myspace"


class TestStorachaCLITokens:
    """Tests for token management methods."""

    def test_generate_bridge_tokens(self, cli):
        """Test generate_bridge_tokens parses JSON output."""
        cli.config["agent_did"] = "did:key:agent"
        cli.config["space_did"] = "did:key:space"

        mock_agent_result = MagicMock()
        mock_agent_result.returncode = 0
        mock_agent_result.stdout = "did:key:agent"

        mock_space_result = MagicMock()
        mock_space_result.returncode = 0
        mock_space_result.stdout = "DID: did:key:space"

        mock_tokens_result = MagicMock()
        mock_tokens_result.returncode = 0
        mock_tokens_result.stdout = json.dumps(
            {
                "X-Auth-Secret": "test-secret",
                "Authorization": "test-auth",
            }
        )

        def run_cli_side_effect(args, **kwargs):
            if args[0] == "whoami":
                return mock_agent_result
            elif args[:2] == ["space", "info"]:
                return mock_space_result
            elif args[:2] == ["bridge", "generate-tokens"]:
                return mock_tokens_result
            return MagicMock(returncode=1)

        with patch.object(cli, "_run_cli", side_effect=run_cli_side_effect):
            with patch.object(cli, "get_current_space", return_value="did:key:space"):
                tokens = cli.generate_bridge_tokens()

                assert tokens is not None
                assert tokens.x_auth_secret == "test-secret"
                assert tokens.authorization == "test-auth"
                assert tokens.agent_did == "did:key:agent"

    def test_get_bridge_tokens_from_cache(self, cli):
        """Test get_bridge_tokens returns cached non-expired tokens."""
        future = datetime.utcnow() + timedelta(hours=1)
        cli.config["bridge_tokens"] = {
            "x_auth_secret": "cached-secret",
            "authorization": "cached-auth",
            "agent_did": "did:key:agent",
            "space_did": "did:key:space",
            "capabilities": ["store/add"],
            "expires_at": future.isoformat(),
        }

        tokens = cli.get_bridge_tokens(auto_refresh=False)
        assert tokens is not None
        assert tokens.x_auth_secret == "cached-secret"


class TestStorachaCLIGetStatus:
    """Tests for get_status method."""

    def test_get_status_returns_dict(self, cli):
        """Test get_status returns comprehensive status."""
        with patch.object(cli, "is_cli_installed", return_value=True):
            with patch.object(cli, "is_authenticated", return_value=False):
                with patch.object(cli, "get_agent_did", return_value="did:key:test"):
                    with patch.object(cli, "get_current_space", return_value=None):
                        with patch.object(cli, "list_spaces", return_value=[]):
                            status = cli.get_status()

                            assert "cli_installed" in status
                            assert "authenticated" in status
                            assert "agent_did" in status
                            assert "space_did" in status
                            assert "spaces" in status
                            assert "has_tokens" in status
                            assert "config_path" in status
