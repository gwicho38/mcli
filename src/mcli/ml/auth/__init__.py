"""Authentication and authorization system."""

from .auth_manager import (
    AuthManager,
    create_access_token,
    get_current_active_user,
    get_current_user,
    hash_password,
    require_role,
    verify_access_token,
    verify_password,
)
from .models import (
    PasswordChange,
    PasswordReset,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from .permissions import Permission, check_permission, has_permission

__all__ = [
    "AuthManager",
    "create_access_token",
    "verify_access_token",
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "hash_password",
    "verify_password",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "PasswordReset",
    "PasswordChange",
    "Permission",
    "check_permission",
    "has_permission",
]
