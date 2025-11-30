"""
Storacha CLI wrapper for authentication and token generation.

Uses the @storacha/cli npm package for:
- Email-based authentication
- Space management
- HTTP bridge token generation

This module does NOT use lsh-framework for secrets management.
Credentials are stored in MCLI's own config at ~/.mcli/storacha-config.json.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcli.lib.constants import StorachaBridgeCapabilities, StorageMessages, StoragePaths
from mcli.lib.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BridgeTokens:
    """HTTP bridge authentication tokens."""

    x_auth_secret: str
    authorization: str
    agent_did: str
    space_did: str
    capabilities: list[str]
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if tokens are expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers dict."""
        return {
            "X-Auth-Secret": self.x_auth_secret,
            "Authorization": self.authorization,
        }


class StorachaCLI:
    """
    Wrapper for the Storacha CLI (@storacha/cli npm package).

    Provides Python interface to:
    - Login with email verification
    - Create and select spaces
    - Generate HTTP bridge tokens
    - Store credentials in MCLI config
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize Storacha CLI wrapper.

        Args:
            config_path: Optional custom config path (default: ~/.mcli/storacha-config.json)
        """
        self.config_path = config_path or Path.home() / StoragePaths.STORACHA_CONFIG_FILE
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from disk."""
        if self.config_path.exists():
            try:
                content = self.config_path.read_text()
                result: dict[str, Any] = json.loads(content)
                return result
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        return {}

    def _save_config(self) -> None:
        """Save configuration to disk."""
        try:
            content = json.dumps(self.config, indent=2)
            self.config_path.write_text(content)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def _run_cli(
        self, args: list[str], timeout: int = 60, check: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run storacha CLI command.

        Args:
            args: Command arguments (without 'storacha' prefix)
            timeout: Command timeout in seconds
            check: Raise exception on non-zero exit

        Returns:
            CompletedProcess result

        Raises:
            FileNotFoundError: If storacha CLI not installed
            subprocess.CalledProcessError: If command fails and check=True
        """
        cli_path = shutil.which("storacha")
        if not cli_path:
            raise FileNotFoundError(StorageMessages.STORACHA_CLI_NOT_FOUND)

        cmd = [cli_path] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)

        if result.returncode != 0:
            logger.debug(f"CLI stderr: {result.stderr}")

        return result

    def is_cli_installed(self) -> bool:
        """Check if storacha CLI is installed."""
        return shutil.which("storacha") is not None

    def get_agent_did(self) -> Optional[str]:
        """
        Get the agent DID (decentralized identifier).

        Returns:
            Optional[str]: Agent DID, or None if not found
        """
        try:
            result = self._run_cli(["whoami"], check=False)
            if result.returncode == 0 and result.stdout.strip():
                did: str = result.stdout.strip()
                if did.startswith("did:key:"):
                    self.config["agent_did"] = did
                    self._save_config()
                    return did
        except Exception as e:
            logger.debug(f"Failed to get agent DID: {e}")
        return self.config.get("agent_did")

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated with Storacha.

        Returns:
            bool: True if authenticated with at least one account
        """
        try:
            result = self._run_cli(["account", "ls"], check=False)
            # If no accounts, CLI returns error about authorization
            if "Agent has not been authorized" in result.stderr:
                return False
            # Check if we have any accounts listed
            return bool(result.stdout.strip())
        except Exception:
            return False

    def login(self, email: str) -> bool:
        """
        Login with email verification.

        Args:
            email: Email address for authentication

        Returns:
            bool: True if login successful

        Note:
            This is an interactive process - user must click email link.
        """
        logger.info(StorageMessages.STORACHA_SENDING_VERIFICATION.format(email=email))
        logger.info(StorageMessages.STORACHA_CHECK_EMAIL)

        try:
            # This command waits for email verification
            result = self._run_cli(["login", email], timeout=300, check=False)

            if result.returncode == 0:
                self.config["email"] = email
                self.config["logged_in_at"] = datetime.utcnow().isoformat()
                self._save_config()
                logger.info(StorageMessages.STORACHA_LOGIN_SUCCESS)
                return True
            else:
                logger.error(StorageMessages.STORACHA_LOGIN_FAILED.format(error=result.stderr))
                return False

        except subprocess.TimeoutExpired:
            logger.error("Login timed out - email verification not completed")
            return False
        except Exception as e:
            logger.error(StorageMessages.STORACHA_LOGIN_FAILED.format(error=str(e)))
            return False

    def list_spaces(self) -> list[str]:
        """
        List available spaces.

        Returns:
            List[str]: List of space DIDs
        """
        try:
            result = self._run_cli(["space", "ls"], check=False)
            if result.returncode == 0:
                # Parse space list (format: "* did:key:xxx" or "  did:key:xxx")
                spaces = []
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("*"):
                        line = line[1:].strip()
                    if line.startswith("did:"):
                        spaces.append(line)
                return spaces
        except Exception as e:
            logger.debug(f"Failed to list spaces: {e}")
        return []

    def get_current_space(self) -> Optional[str]:
        """
        Get the currently selected space.

        Returns:
            Optional[str]: Current space DID, or None
        """
        try:
            result = self._run_cli(["space", "info"], check=False)
            if result.returncode == 0:
                # Parse space info output for DID
                for line in result.stdout.split("\n"):
                    if "DID:" in line:
                        parts = line.split("DID:")
                        if len(parts) > 1:
                            did: str = parts[1].strip()
                            if did.startswith("did:"):
                                return did
                    # Also check for just the DID on its own line
                    stripped_line: str = line.strip()
                    if stripped_line.startswith("did:key:"):
                        return stripped_line
        except Exception as e:
            logger.debug(f"Failed to get current space: {e}")
        return self.config.get("space_did")

    def create_space(self, name: Optional[str] = None) -> Optional[str]:
        """
        Create a new space.

        Args:
            name: Optional space name

        Returns:
            Optional[str]: Space DID if created, None on failure
        """
        try:
            args = ["space", "create"]
            if name:
                args.append(name)

            result = self._run_cli(args, check=False)

            if result.returncode == 0:
                # Parse created space DID from output
                output = result.stdout + result.stderr
                for line in output.split("\n"):
                    line = line.strip()
                    if line.startswith("did:key:"):
                        space_did: str = line
                        self.config["space_did"] = space_did
                        self._save_config()
                        logger.info(
                            StorageMessages.STORACHA_SPACE_CREATED.format(space_did=space_did)
                        )
                        return space_did
            else:
                logger.error(f"Failed to create space: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to create space: {e}")
        return None

    def select_space(self, space_did: str) -> bool:
        """
        Select a space to use.

        Args:
            space_did: Space DID to select

        Returns:
            bool: True if selection successful
        """
        try:
            result = self._run_cli(["space", "use", space_did], check=False)
            if result.returncode == 0:
                self.config["space_did"] = space_did
                self._save_config()
                logger.info(StorageMessages.STORACHA_SPACE_SELECTED.format(space_did=space_did))
                return True
            else:
                logger.error(f"Failed to select space: {result.stderr}")
        except Exception as e:
            logger.error(f"Failed to select space: {e}")
        return False

    def generate_bridge_tokens(
        self,
        capabilities: Optional[list[str]] = None,
        expiration_hours: int = 24,
    ) -> Optional[BridgeTokens]:
        """
        Generate HTTP bridge authentication tokens.

        Uses 'storacha bridge generate-tokens' to create X-Auth-Secret
        and Authorization headers for HTTP API access.

        Args:
            capabilities: List of capabilities to delegate (default: upload capabilities)
            expiration_hours: Token expiration in hours (default: 24)

        Returns:
            Optional[BridgeTokens]: Generated tokens, or None on failure
        """
        agent_did = self.get_agent_did()
        if not agent_did:
            logger.error("No agent DID found")
            return None

        space_did = self.get_current_space()
        if not space_did:
            logger.error(StorageMessages.STORACHA_NO_SPACES)
            return None

        if capabilities is None:
            capabilities = StorachaBridgeCapabilities.ALL_CAPABILITIES

        try:
            # Calculate expiration timestamp
            expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)
            expiration_ts = int(expires_at.timestamp())

            # Build command
            args = ["bridge", "generate-tokens", agent_did, "--json"]

            # Add capabilities
            for cap in capabilities:
                args.extend(["--can", cap])

            # Add expiration
            args.extend(["--expiration", str(expiration_ts)])

            result = self._run_cli(args, check=False)

            if result.returncode == 0:
                # Parse JSON output
                try:
                    tokens_json = json.loads(result.stdout)
                    tokens = BridgeTokens(
                        x_auth_secret=tokens_json.get("X-Auth-Secret", ""),
                        authorization=tokens_json.get("Authorization", ""),
                        agent_did=agent_did,
                        space_did=space_did,
                        capabilities=capabilities,
                        expires_at=expires_at,
                    )

                    # Save to config
                    self.config["bridge_tokens"] = {
                        "x_auth_secret": tokens.x_auth_secret,
                        "authorization": tokens.authorization,
                        "agent_did": tokens.agent_did,
                        "space_did": tokens.space_did,
                        "capabilities": tokens.capabilities,
                        "expires_at": tokens.expires_at.isoformat() if tokens.expires_at else None,
                    }
                    self._save_config()

                    logger.info(StorageMessages.STORACHA_TOKENS_GENERATED)
                    return tokens

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse token JSON: {e}")
                    logger.debug(f"Output: {result.stdout}")
            else:
                logger.error(f"Failed to generate tokens: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to generate bridge tokens: {e}")

        return None

    def get_bridge_tokens(self, auto_refresh: bool = True) -> Optional[BridgeTokens]:
        """
        Get HTTP bridge tokens, refreshing if expired.

        Args:
            auto_refresh: If True, regenerate expired tokens

        Returns:
            Optional[BridgeTokens]: Valid tokens, or None if unavailable
        """
        # Check for cached tokens
        cached = self.config.get("bridge_tokens")
        if cached:
            try:
                expires_at = None
                if cached.get("expires_at"):
                    expires_at = datetime.fromisoformat(cached["expires_at"])

                tokens = BridgeTokens(
                    x_auth_secret=cached["x_auth_secret"],
                    authorization=cached["authorization"],
                    agent_did=cached["agent_did"],
                    space_did=cached["space_did"],
                    capabilities=cached.get("capabilities", []),
                    expires_at=expires_at,
                )

                if not tokens.is_expired():
                    return tokens

                # Token expired
                if auto_refresh:
                    logger.info(StorageMessages.STORACHA_TOKENS_EXPIRED)
                    return self.generate_bridge_tokens(capabilities=tokens.capabilities)

            except Exception as e:
                logger.debug(f"Failed to load cached tokens: {e}")

        # No valid cached tokens, try to generate new ones
        if auto_refresh and self.is_authenticated():
            return self.generate_bridge_tokens()

        return None

    def upload_file(self, file_path: Path) -> Optional[str]:
        """
        Upload a file using the storacha CLI directly.

        This is a convenience method that uses the CLI's 'up' command
        instead of the HTTP bridge API.

        Args:
            file_path: Path to file to upload

        Returns:
            Optional[str]: CID of uploaded content, or None on failure
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        try:
            result = self._run_cli(["up", str(file_path)], timeout=120, check=False)

            if result.returncode == 0:
                # Parse CID from output (format varies)
                output = result.stdout + result.stderr
                for line in output.split("\n"):
                    line = line.strip()
                    # Look for CID pattern (bafkrei... or bafy...)
                    if line.startswith("baf"):
                        cid_parts = line.split()
                        if cid_parts:
                            return str(cid_parts[0])  # Get just the CID
                    # Or look for gateway URL
                    if "storacha.link" in line and "/ipfs/" in line:
                        # Extract CID from URL
                        parts = line.split("/ipfs/")
                        if len(parts) > 1:
                            cid: str = parts[1].split("/")[0].split("?")[0]
                            return cid

                logger.warning(f"Could not parse CID from output: {output}")
            else:
                logger.error(f"Upload failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")

        return None

    def list_uploads(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        List recent uploads.

        Args:
            limit: Maximum number of uploads to return

        Returns:
            List[Dict[str, Any]]: List of upload records
        """
        try:
            result = self._run_cli(["ls"], check=False)

            if result.returncode == 0:
                uploads = []
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("─"):  # Skip separator lines
                        # Parse upload entry (format varies by CLI version)
                        parts = line.split()
                        if parts and parts[0].startswith("baf"):
                            uploads.append({"cid": parts[0], "raw": line})
                        if len(uploads) >= limit:
                            break
                return uploads

        except Exception as e:
            logger.debug(f"Failed to list uploads: {e}")

        return []

    def get_status(self) -> dict[str, Any]:
        """
        Get current Storacha status.

        Returns:
            Dict[str, Any]: Status information
        """
        return {
            "cli_installed": self.is_cli_installed(),
            "authenticated": self.is_authenticated(),
            "agent_did": self.get_agent_did(),
            "space_did": self.get_current_space(),
            "spaces": self.list_spaces(),
            "has_tokens": bool(self.config.get("bridge_tokens")),
            "config_path": str(self.config_path),
        }
