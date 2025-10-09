"""Authentication data models"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class UserCreate(BaseModel):
    """User registration model"""

    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)

    @validator("password")
    def validate_password(cls, v):
        """Ensure password meets security requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class UserLogin(BaseModel):
    """User login model"""

    username: str
    password: str


class UserResponse(BaseModel):
    """User response model"""

    id: UUID
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: UserResponse


class TokenData(BaseModel):
    """JWT token payload"""

    sub: str  # User ID
    username: str
    role: str
    exp: datetime
    iat: datetime
    jti: Optional[str] = None  # JWT ID for token revocation


class PasswordReset(BaseModel):
    """Password reset request"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordChange(BaseModel):
    """Password change request"""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator("new_password")
    def validate_password(cls, v, values):
        """Ensure new password is different and meets requirements"""
        if "current_password" in values and v == values["current_password"]:
            raise ValueError("New password must be different from current password")

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class APIKeyCreate(BaseModel):
    """API key creation model"""

    name: str = Field(..., min_length=1, max_length=100)
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API key response"""

    key: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]


class UserUpdate(BaseModel):
    """User update model"""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    role: Optional[str] = None


class UserPermissions(BaseModel):
    """User permissions model"""

    user_id: UUID
    permissions: List[str]
    roles: List[str]


class SessionInfo(BaseModel):
    """Session information"""

    session_id: str
    user_id: UUID
    ip_address: str
    user_agent: str
    created_at: datetime
    expires_at: datetime
    is_active: bool


class LoginAttempt(BaseModel):
    """Login attempt tracking"""

    username: str
    ip_address: str
    success: bool
    timestamp: datetime
    failure_reason: Optional[str] = None
