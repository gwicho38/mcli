"""Test suite for authentication and authorization"""

import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.orm import Session

# Check for aiosqlite dependency
try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

if HAS_AIOSQLITE:
    from mcli.ml.auth.auth_manager import AuthManager, RateLimiter
    from mcli.ml.auth.models import UserCreate, UserLogin, PasswordChange
    from mcli.ml.auth.permissions import Permission, has_permission, check_permission
    from mcli.ml.database.models import User, UserRole


@pytest.mark.skipif(not HAS_AIOSQLITE, reason="aiosqlite module not installed")
class TestAuthManager:
    """Test authentication manager"""

    @pytest.fixture
    def auth_manager(self):
        """Create auth manager instance"""
        return AuthManager()

    @pytest.fixture
    def mock_user(self):
        """Create mock user"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.username = "testuser"
        user.email = "test@example.com"
        user.password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN4kAaKRcKGdGqHGKJIJu"  # "password123"
        user.role = UserRole.USER
        user.is_active = True
        user.is_verified = True
        return user

    def test_password_hashing(self, auth_manager):
        """Test password hashing and verification"""
        password = "SecurePassword123!"

        hashed = auth_manager.hash_password(password)
        assert hashed != password
        assert auth_manager.verify_password(password, hashed)
        assert not auth_manager.verify_password("WrongPassword", hashed)

    def test_jwt_token_creation(self, auth_manager):
        """Test JWT token creation"""
        user_id = "test-user-123"
        username = "testuser"
        role = "user"

        token = auth_manager.create_access_token(user_id, username, role)
        assert token is not None
        assert isinstance(token, str)

        # Decode token
        payload = jwt.decode(
            token,
            auth_manager.secret_key,
            algorithms=[auth_manager.algorithm]
        )
        assert payload["sub"] == user_id
        assert payload["username"] == username
        assert payload["role"] == role

    def test_token_verification(self, auth_manager):
        """Test token verification"""
        token = auth_manager.create_access_token(
            "user-123",
            "testuser",
            "user"
        )

        token_data = auth_manager.verify_token(token)
        assert token_data.sub == "user-123"
        assert token_data.username == "testuser"
        assert token_data.role == "user"

    def test_expired_token(self, auth_manager):
        """Test expired token handling"""
        # Create token that expires immediately
        token = auth_manager.create_access_token(
            "user-123",
            "testuser",
            "user",
            expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token(token)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_registration(self, auth_manager):
        """Test user registration"""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="SecurePass123!",
            first_name="New",
            last_name="User"
        )

        user = await auth_manager.register_user(user_data, mock_db)
        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_user_login(self, auth_manager, mock_user):
        """Test user login"""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_db.commit = Mock()

        # Mock password verification
        with patch.object(auth_manager, 'verify_password', return_value=True):
            login_data = UserLogin(username="testuser", password="password123")
            token_response = await auth_manager.login(login_data, mock_db)

            assert token_response.access_token is not None
            assert token_response.refresh_token is not None
            assert token_response.user.username == "testuser"

    @pytest.mark.asyncio
    async def test_invalid_login(self, auth_manager):
        """Test invalid login credentials"""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        login_data = UserLogin(username="invalid", password="wrong")

        with pytest.raises(HTTPException) as exc_info:
            await auth_manager.login(login_data, mock_db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, auth_manager, mock_user):
        """Test refresh token functionality"""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        refresh_token = auth_manager.create_refresh_token(str(mock_user.id))

        new_token_response = await auth_manager.refresh_access_token(
            refresh_token,
            mock_db
        )

        assert new_token_response.access_token is not None


@pytest.mark.skipif(not HAS_AIOSQLITE, reason="aiosqlite module not installed")
class TestPasswordValidation:
    """Test password validation"""

    def test_password_requirements(self):
        """Test password meets requirements"""
        # Valid password
        valid_user = UserCreate(
            username="user",
            email="user@example.com",
            password="ValidPass123!"
        )
        assert valid_user.password == "ValidPass123!"

        # Too short
        with pytest.raises(ValueError, match="at least 8 characters"):
            UserCreate(
                username="user",
                email="user@example.com",
                password="Short1!"
            )

        # No digit
        with pytest.raises(ValueError, match="at least one digit"):
            UserCreate(
                username="user",
                email="user@example.com",
                password="NoDigitPass!"
            )

        # No uppercase
        with pytest.raises(ValueError, match="at least one uppercase"):
            UserCreate(
                username="user",
                email="user@example.com",
                password="nouppercase123!"
            )

    def test_password_change_validation(self):
        """Test password change validation"""
        # Valid change
        valid_change = PasswordChange(
            current_password="OldPass123!",
            new_password="NewPass456!"
        )
        assert valid_change.new_password == "NewPass456!"

        # Same as current
        with pytest.raises(ValueError, match="must be different"):
            PasswordChange(
                current_password="SamePass123!",
                new_password="SamePass123!"
            )


@pytest.mark.skipif(not HAS_AIOSQLITE, reason="aiosqlite module not installed")
class TestPermissions:
    """Test permission system"""

    @pytest.fixture
    def admin_user(self):
        """Create admin user"""
        user = Mock(spec=User)
        user.role = UserRole.ADMIN
        return user

    @pytest.fixture
    def regular_user(self):
        """Create regular user"""
        user = Mock(spec=User)
        user.role = UserRole.USER
        return user

    def test_admin_permissions(self, admin_user):
        """Test admin has all permissions"""
        for permission in Permission:
            assert has_permission(admin_user, permission)

    def test_user_permissions(self, regular_user):
        """Test regular user permissions"""
        # Should have
        assert has_permission(regular_user, Permission.MODEL_VIEW)
        assert has_permission(regular_user, Permission.PORTFOLIO_CREATE)

        # Should not have
        assert not has_permission(regular_user, Permission.MODEL_DELETE)
        assert not has_permission(regular_user, Permission.ADMIN_ACCESS)

    def test_check_permission_raises(self, regular_user):
        """Test permission check raises exception"""
        with pytest.raises(HTTPException) as exc_info:
            check_permission(regular_user, Permission.ADMIN_ACCESS)
        assert exc_info.value.status_code == 403

    def test_role_based_permissions(self):
        """Test different role permissions"""
        viewer = Mock(spec=User, role=UserRole.VIEWER)
        analyst = Mock(spec=User, role=UserRole.ANALYST)

        # Viewer - read only
        assert has_permission(viewer, Permission.MODEL_VIEW)
        assert not has_permission(viewer, Permission.MODEL_CREATE)

        # Analyst - more permissions
        assert has_permission(analyst, Permission.MODEL_CREATE)
        assert has_permission(analyst, Permission.MODEL_DEPLOY)
        assert not has_permission(analyst, Permission.USER_DELETE)


@pytest.mark.skipif(not HAS_AIOSQLITE, reason="aiosqlite module not installed")
class TestRateLimiter:
    """Test rate limiting"""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter"""
        return RateLimiter(requests=5, window=60)

    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests(self, rate_limiter):
        """Test rate limiter allows requests within limit"""
        client_id = "127.0.0.1"

        for _ in range(5):
            allowed = await rate_limiter.check_rate_limit(client_id)
            assert allowed

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excess(self, rate_limiter):
        """Test rate limiter blocks excess requests"""
        client_id = "127.0.0.1"

        # Use up limit
        for _ in range(5):
            await rate_limiter.check_rate_limit(client_id)

        # Should be blocked
        allowed = await rate_limiter.check_rate_limit(client_id)
        assert not allowed

    @pytest.mark.asyncio
    async def test_rate_limit_separate_clients(self, rate_limiter):
        """Test rate limiting is per client"""
        client1 = "127.0.0.1"
        client2 = "127.0.0.2"

        # Use up client1's limit
        for _ in range(5):
            await rate_limiter.check_rate_limit(client1)

        # Client2 should still be allowed
        allowed = await rate_limiter.check_rate_limit(client2)
        assert allowed


@pytest.mark.skipif(not HAS_AIOSQLITE, reason="aiosqlite module not installed")
class TestResourcePermissions:
    """Test resource-based permissions"""

    def test_portfolio_edit_permission(self):
        """Test portfolio edit permissions"""
        from mcli.ml.auth.permissions import ResourcePermission

        owner = Mock(spec=User, id="user1", role=UserRole.USER)
        other_user = Mock(spec=User, id="user2", role=UserRole.USER)
        admin = Mock(spec=User, id="admin", role=UserRole.ADMIN)

        portfolio = Mock(user_id="user1")

        # Owner can edit
        assert ResourcePermission.can_edit_portfolio(owner, portfolio)

        # Other user cannot
        assert not ResourcePermission.can_edit_portfolio(other_user, portfolio)

        # Admin can edit any
        assert ResourcePermission.can_edit_portfolio(admin, portfolio)

    def test_model_deployment_permission(self):
        """Test model deployment permissions"""
        from mcli.ml.auth.permissions import ResourcePermission

        user = Mock(spec=User, role=UserRole.USER)
        analyst = Mock(spec=User, role=UserRole.ANALYST)
        admin = Mock(spec=User, role=UserRole.ADMIN)
        model = Mock()

        assert not ResourcePermission.can_deploy_model(user, model)
        assert ResourcePermission.can_deploy_model(analyst, model)
        assert ResourcePermission.can_deploy_model(admin, model)


@pytest.mark.skipif(not HAS_AIOSQLITE, reason="aiosqlite module not installed")
class TestAuthIntegration:
    """Integration tests for auth system"""

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self):
        """Test complete authentication flow"""
        auth_manager = AuthManager()
        mock_db = Mock(spec=Session)

        # Register user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="SecurePass123!"
        )

        # Simulate registration
        with patch.object(auth_manager, 'register_user') as mock_register:
            mock_user = Mock(
                id="user-123",
                username="testuser",
                email="test@example.com",
                role=UserRole.USER,
                is_active=True
            )
            mock_register.return_value = mock_user

            registered_user = await auth_manager.register_user(user_data, mock_db)

        # Login
        with patch.object(auth_manager, 'authenticate_user') as mock_auth:
            mock_auth.return_value = mock_user

            login_data = UserLogin(username="testuser", password="SecurePass123!")
            token_response = await auth_manager.login(login_data, mock_db)

            assert token_response.access_token is not None

        # Verify token
        token_data = auth_manager.verify_token(token_response.access_token)
        assert token_data.username == "testuser"