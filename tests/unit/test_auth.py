"""
Unit tests for mcli.lib.auth modules
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os


class TestAuth:
    """Test suite for auth module"""

    def test_requires_auth_decorator(self):
        """Test requires_auth decorator"""
        from mcli.lib.auth.auth import requires_auth

        @requires_auth
        def protected_function():
            return "success"

        with patch('mcli.lib.auth.auth.is_authenticated', return_value=True):
            result = protected_function()
            assert result == "success"

    def test_requires_auth_not_authenticated(self):
        """Test requires_auth when not authenticated"""
        from mcli.lib.auth.auth import requires_auth

        @requires_auth
        def protected_function():
            return "success"

        with patch('mcli.lib.auth.auth.is_authenticated', return_value=False):
            with pytest.raises(Exception):
                protected_function()

    def test_is_authenticated_true(self):
        """Test is_authenticated returns True when token exists"""
        from mcli.lib.auth.auth import is_authenticated

        with patch('mcli.lib.auth.auth.get_auth_token', return_value='valid_token'):
            assert is_authenticated() is True

    def test_is_authenticated_false(self):
        """Test is_authenticated returns False when no token"""
        from mcli.lib.auth.auth import is_authenticated

        with patch('mcli.lib.auth.auth.get_auth_token', return_value=None):
            assert is_authenticated() is False

    def test_get_auth_token(self):
        """Test getting auth token"""
        from mcli.lib.auth.auth import get_auth_token

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / '.mcli_token'
            token_file.write_text('test_token_123')

            with patch('mcli.lib.auth.auth.TOKEN_FILE', token_file):
                result = get_auth_token()
                assert result == 'test_token_123'

    def test_get_auth_token_no_file(self):
        """Test getting auth token when file doesn't exist"""
        from mcli.lib.auth.auth import get_auth_token

        with patch('mcli.lib.auth.auth.TOKEN_FILE') as mock_path:
            mock_path.exists.return_value = False

            result = get_auth_token()
            assert result is None

    def test_set_auth_token(self):
        """Test setting auth token"""
        from mcli.lib.auth.auth import set_auth_token

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / '.mcli_token'

            with patch('mcli.lib.auth.auth.TOKEN_FILE', token_file):
                set_auth_token('new_token')

                assert token_file.exists()
                assert token_file.read_text() == 'new_token'

    def test_clear_auth_token(self):
        """Test clearing auth token"""
        from mcli.lib.auth.auth import clear_auth_token

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / '.mcli_token'
            token_file.write_text('token_to_clear')

            with patch('mcli.lib.auth.auth.TOKEN_FILE', token_file):
                clear_auth_token()

                assert not token_file.exists()


class TestCredentialManager:
    """Test suite for credential_manager module"""

    def test_credential_manager_init(self):
        """Test CredentialManager initialization"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / 'credentials.json'

            manager = CredentialManager(str(cred_file))

            assert manager.credentials_file == cred_file
            assert manager.credentials == {}

    def test_store_credential(self):
        """Test storing credentials"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / 'credentials.json'

            manager = CredentialManager(str(cred_file))
            manager.store_credential('aws', 'key123', {'secret': 'value'})

            assert 'aws' in manager.credentials
            assert 'key123' in manager.credentials['aws']

    def test_get_credential(self):
        """Test getting credentials"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / 'credentials.json'

            manager = CredentialManager(str(cred_file))
            manager.store_credential('aws', 'key123', {'secret': 'value'})

            result = manager.get_credential('aws', 'key123')
            assert result == {'secret': 'value'}

    def test_get_credential_not_found(self):
        """Test getting non-existent credentials"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / 'credentials.json'

            manager = CredentialManager(str(cred_file))

            result = manager.get_credential('nonexistent', 'key')
            assert result is None

    def test_list_credentials(self):
        """Test listing credentials"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / 'credentials.json'

            manager = CredentialManager(str(cred_file))
            manager.store_credential('aws', 'key1', {'data': 'test1'})
            manager.store_credential('gcp', 'key2', {'data': 'test2'})

            result = manager.list_credentials()

            assert 'aws' in result
            assert 'gcp' in result
            assert len(result['aws']) == 1
            assert len(result['gcp']) == 1

    def test_delete_credential(self):
        """Test deleting credentials"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / 'credentials.json'

            manager = CredentialManager(str(cred_file))
            manager.store_credential('aws', 'key123', {'secret': 'value'})

            result = manager.delete_credential('aws', 'key123')
            assert result is True

            # Verify it's gone
            assert manager.get_credential('aws', 'key123') is None

    def test_save_and_load(self):
        """Test saving and loading credentials"""
        from mcli.lib.auth.credential_manager import CredentialManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cred_file = Path(tmpdir) / 'credentials.json'

            # Save credentials
            manager1 = CredentialManager(str(cred_file))
            manager1.store_credential('aws', 'key123', {'secret': 'value'})
            manager1.save()

            # Load in new instance
            manager2 = CredentialManager(str(cred_file))
            manager2.load()

            assert manager2.get_credential('aws', 'key123') == {'secret': 'value'}


class TestTokenManager:
    """Test suite for token_manager module"""

    def test_token_manager_get_token(self):
        """Test TokenManager get_token"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TokenManager(str(Path(tmpdir) / 'token.txt'))

            with patch.object(manager, '_load_token', return_value='test_token'):
                result = manager.get_token()
                assert result == 'test_token'

    def test_token_manager_set_token(self):
        """Test TokenManager set_token"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / 'token.txt'
            manager = TokenManager(str(token_file))

            manager.set_token('new_token')

            assert token_file.exists()
            assert token_file.read_text() == 'new_token'

    def test_token_manager_clear_token(self):
        """Test TokenManager clear_token"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / 'token.txt'
            token_file.write_text('token_to_clear')

            manager = TokenManager(str(token_file))
            manager.clear_token()

            assert not token_file.exists()

    def test_token_manager_is_valid(self):
        """Test TokenManager is_valid"""
        from mcli.lib.auth.token_manager import TokenManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TokenManager(str(Path(tmpdir) / 'token.txt'))

            # Mock token validation
            with patch.object(manager, '_validate_token', return_value=True):
                manager.set_token('valid_token')
                assert manager.is_valid() is True


class TestMcliManager:
    """Test suite for mcli_manager module"""

    def test_get_mcli_token(self):
        """Test getting MCLI token"""
        from mcli.lib.auth.mcli_manager import get_mcli_token

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / '.mcli_token'
            token_file.write_text('mcli_token_123')

            with patch('mcli.lib.auth.mcli_manager.TOKEN_FILE', token_file):
                result = get_mcli_token()
                assert result == 'mcli_token_123'

    def test_set_mcli_token(self):
        """Test setting MCLI token"""
        from mcli.lib.auth.mcli_manager import set_mcli_token

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / '.mcli_token'

            with patch('mcli.lib.auth.mcli_manager.TOKEN_FILE', token_file):
                set_mcli_token('new_mcli_token')

                assert token_file.exists()
                assert token_file.read_text() == 'new_mcli_token'

    def test_clear_mcli_token(self):
        """Test clearing MCLI token"""
        from mcli.lib.auth.mcli_manager import clear_mcli_token

        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = Path(tmpdir) / '.mcli_token'
            token_file.write_text('token_to_clear')

            with patch('mcli.lib.auth.mcli_manager.TOKEN_FILE', token_file):
                clear_mcli_token()

                assert not token_file.exists()

    def test_is_authenticated(self):
        """Test is_authenticated check"""
        from mcli.lib.auth.mcli_manager import is_mcli_authenticated

        with patch('mcli.lib.auth.mcli_manager.get_mcli_token', return_value='valid_token'):
            assert is_mcli_authenticated() is True

        with patch('mcli.lib.auth.mcli_manager.get_mcli_token', return_value=None):
            assert is_mcli_authenticated() is False
