"""Permission management system"""

from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from mcli.ml.database.models import User, UserRole


class Permission(Enum):
    """System permissions"""

    # Model permissions
    MODEL_VIEW = "model:view"
    MODEL_CREATE = "model:create"
    MODEL_EDIT = "model:edit"
    MODEL_DELETE = "model:delete"
    MODEL_DEPLOY = "model:deploy"

    # Prediction permissions
    PREDICTION_VIEW = "prediction:view"
    PREDICTION_CREATE = "prediction:create"
    PREDICTION_DELETE = "prediction:delete"

    # Portfolio permissions
    PORTFOLIO_VIEW = "portfolio:view"
    PORTFOLIO_CREATE = "portfolio:create"
    PORTFOLIO_EDIT = "portfolio:edit"
    PORTFOLIO_DELETE = "portfolio:delete"
    PORTFOLIO_TRADE = "portfolio:trade"

    # Data permissions
    DATA_VIEW = "data:view"
    DATA_CREATE = "data:create"
    DATA_EDIT = "data:edit"
    DATA_DELETE = "data:delete"

    # User permissions
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_EDIT = "user:edit"
    USER_DELETE = "user:delete"

    # Admin permissions
    ADMIN_ACCESS = "admin:access"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_MONITORING = "admin:monitoring"
    ADMIN_AUDIT = "admin:audit"

    # System permissions
    SYSTEM_STATUS = "system:status"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_RESTART = "system:restart"


# Role-based permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: set(Permission),  # Admin has all permissions
    UserRole.ANALYST: {
        Permission.MODEL_VIEW,
        Permission.MODEL_CREATE,
        Permission.MODEL_EDIT,
        Permission.MODEL_DEPLOY,
        Permission.PREDICTION_VIEW,
        Permission.PREDICTION_CREATE,
        Permission.PORTFOLIO_VIEW,
        Permission.PORTFOLIO_CREATE,
        Permission.PORTFOLIO_EDIT,
        Permission.DATA_VIEW,
        Permission.DATA_CREATE,
        Permission.DATA_EDIT,
        Permission.SYSTEM_STATUS,
    },
    UserRole.USER: {
        Permission.MODEL_VIEW,
        Permission.PREDICTION_VIEW,
        Permission.PREDICTION_CREATE,
        Permission.PORTFOLIO_VIEW,
        Permission.PORTFOLIO_CREATE,
        Permission.PORTFOLIO_EDIT,
        Permission.PORTFOLIO_TRADE,
        Permission.DATA_VIEW,
        Permission.SYSTEM_STATUS,
    },
    UserRole.VIEWER: {
        Permission.MODEL_VIEW,
        Permission.PREDICTION_VIEW,
        Permission.PORTFOLIO_VIEW,
        Permission.DATA_VIEW,
        Permission.SYSTEM_STATUS,
    },
}


def has_permission(user: User, permission: Permission) -> bool:
    """Check if user has specific permission"""
    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return permission in user_permissions


def check_permission(user: User, permission: Permission) -> None:
    """Check permission and raise exception if not allowed"""
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission denied: {permission.value}"
        )


def require_permission(permission: Permission):
    """Decorator to require specific permission"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from kwargs (assumes it's passed as current_user)
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            check_permission(current_user, permission)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission):
    """Decorator to require any of the specified permissions"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            if not any(has_permission(current_user, p) for p in permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {[p.value for p in permissions]}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(*permissions: Permission):
    """Decorator to require all of the specified permissions"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            for permission in permissions:
                check_permission(current_user, permission)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class PermissionChecker:
    """FastAPI dependency for permission checking"""

    def __init__(self, permission: Permission):
        self.permission = permission

    def __call__(self, current_user: User) -> User:
        check_permission(current_user, self.permission)
        return current_user


# Resource-based permissions
class ResourcePermission:
    """Check permissions for specific resources"""

    @staticmethod
    def can_edit_portfolio(user: User, portfolio) -> bool:
        """Check if user can edit a specific portfolio"""
        # Admin can edit any portfolio
        if user.role == UserRole.ADMIN:
            return True

        # User can edit their own portfolio
        if portfolio.user_id == user.id:
            return True

        return False

    @staticmethod
    def can_view_portfolio(user: User, portfolio) -> bool:
        """Check if user can view a specific portfolio"""
        # Admin can view any portfolio
        if user.role == UserRole.ADMIN:
            return True

        # User can view their own portfolio
        if portfolio.user_id == user.id:
            return True

        # Analyst can view any portfolio
        if user.role == UserRole.ANALYST:
            return True

        return False

    @staticmethod
    def can_delete_model(user: User, model) -> bool:
        """Check if user can delete a specific model"""
        # Only admin can delete models
        return user.role == UserRole.ADMIN

    @staticmethod
    def can_deploy_model(user: User, model) -> bool:
        """Check if user can deploy a specific model"""
        # Admin and Analyst can deploy models
        return user.role in [UserRole.ADMIN, UserRole.ANALYST]


# Audit logging
class AuditLogger:
    """Log permission-related actions"""

    @staticmethod
    async def log_access(
        user: User,
        resource: str,
        action: str,
        success: bool,
        details: Dict[str, Any] = None,
        db: Session = None,
    ):
        """Log access attempt"""
        log_entry = {
            "user_id": str(user.id),
            "username": user.username,
            "resource": resource,
            "action": action,
            "success": success,
            "timestamp": datetime.utcnow(),
            "details": details or {},
        }

        # In production, save to database or logging service
        print(f"AUDIT: {log_entry}")


# Permission groups for easier management
class PermissionGroup:
    """Predefined permission groups"""

    BASIC_USER = {
        Permission.MODEL_VIEW,
        Permission.PREDICTION_VIEW,
        Permission.PORTFOLIO_VIEW,
        Permission.DATA_VIEW,
    }

    TRADER = BASIC_USER | {
        Permission.PREDICTION_CREATE,
        Permission.PORTFOLIO_CREATE,
        Permission.PORTFOLIO_EDIT,
        Permission.PORTFOLIO_TRADE,
    }

    DATA_SCIENTIST = TRADER | {
        Permission.MODEL_CREATE,
        Permission.MODEL_EDIT,
        Permission.DATA_CREATE,
        Permission.DATA_EDIT,
    }

    ADMIN = set(Permission)  # All permissions
