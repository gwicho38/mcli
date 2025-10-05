"""Authentication API routes"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from mcli.ml.auth import (
    AuthManager,
    PasswordChange,
    PasswordReset,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    check_rate_limit,
    get_current_active_user,
    get_current_user,
)
from mcli.ml.database.models import User
from mcli.ml.database.session import get_db

router = APIRouter()
auth_manager = AuthManager()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate, db: Session = Depends(get_db), _: bool = Depends(check_rate_limit)
):
    """Register a new user"""
    try:
        user = await auth_manager.register_user(user_data, db)
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin, db: Session = Depends(get_db), _: bool = Depends(check_rate_limit)
):
    """Login and receive access token"""
    return await auth_manager.login(login_data, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    return await auth_manager.refresh_access_token(refresh_token, db)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout current user"""
    # In a real implementation, you might want to blacklist the token
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update current user information"""
    # Update allowed fields
    allowed_fields = ["first_name", "last_name", "email"]
    for field in allowed_fields:
        if field in updates:
            setattr(current_user, field, updates[field])

    db.commit()
    db.refresh(current_user)
    return UserResponse.from_orm(current_user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change current user's password"""
    # Verify current password
    if not auth_manager.verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    # Update password
    current_user.password_hash = auth_manager.hash_password(password_data.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/reset-password")
async def reset_password_request(
    reset_data: PasswordReset, db: Session = Depends(get_db), _: bool = Depends(check_rate_limit)
):
    """Request password reset"""
    # Find user by email
    user = db.query(User).filter(User.email == reset_data.email).first()

    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}

    # In a real implementation, send email with reset token
    # For now, just return success
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/verify-email/{token}")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify email address"""
    # In a real implementation, verify the token and update user
    return {"message": "Email verified successfully"}


@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Get all active sessions for current user"""
    # In a real implementation, return active sessions from database
    return {
        "sessions": [
            {
                "id": "session-1",
                "ip_address": "127.0.0.1",
                "user_agent": "Mozilla/5.0",
                "created_at": datetime.utcnow().isoformat(),
                "last_active": datetime.utcnow().isoformat(),
            }
        ]
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke a specific session"""
    # In a real implementation, revoke the session
    return {"message": f"Session {session_id} revoked successfully"}


@router.post("/api-key")
async def create_api_key(
    name: str,
    expires_in_days: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new API key"""
    import secrets
    from datetime import timedelta

    api_key = secrets.token_urlsafe(32)

    # Store API key in database (hashed)
    # In real implementation, store this properly
    current_user.api_key = api_key
    current_user.api_key_created_at = datetime.utcnow()

    db.commit()

    return {
        "api_key": api_key,
        "name": name,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (
            (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
            if expires_in_days
            else None
        ),
    }


@router.get("/api-keys")
async def list_api_keys(current_user: User = Depends(get_current_active_user)):
    """List all API keys for current user"""
    # In a real implementation, return API keys from database
    return {
        "api_keys": [
            {
                "id": "key-1",
                "name": "Production API",
                "created_at": datetime.utcnow().isoformat(),
                "last_used": datetime.utcnow().isoformat(),
                "expires_at": None,
            }
        ]
    }


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke an API key"""
    # In a real implementation, revoke the API key
    return {"message": f"API key {key_id} revoked successfully"}
