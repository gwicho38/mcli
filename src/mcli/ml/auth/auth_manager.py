"""Authentication manager with JWT support"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from mcli.ml.config import settings
from mcli.ml.database.models import User, UserRole
from mcli.ml.database.session import get_db

from .models import TokenData, TokenResponse, UserCreate, UserLogin, UserResponse

# Security scheme
security = HTTPBearer()


class AuthManager:
    """Authentication and authorization manager"""

    def __init__(self):
        self.secret_key = settings.api.secret_key
        self.algorithm = settings.api.algorithm
        self.access_token_expire_minutes = settings.api.access_token_expire_minutes
        self.refresh_token_expire_days = 7

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    def create_access_token(
        self, user_id: str, username: str, role: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32),  # JWT ID for token revocation
        }

        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a refresh token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(32),
        }

        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            token_data = TokenData(
                sub=payload.get("sub"),
                username=payload.get("username"),
                role=payload.get("role"),
                exp=datetime.fromtimestamp(payload.get("exp")),
                iat=datetime.fromtimestamp(payload.get("iat")),
                jti=payload.get("jti"),
            )

            return token_data

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def register_user(self, user_data: UserCreate, db: Session) -> User:
        """Register a new user"""
        # Check if user already exists
        existing_user = (
            db.query(User)
            .filter((User.username == user_data.username) | (User.email == user_data.email))
            .first()
        )

        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
                )

        # Create new user
        hashed_password = self.hash_password(user_data.password)

        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user

    async def authenticate_user(self, login_data: UserLogin, db: Session) -> Optional[User]:
        """Authenticate a user"""
        user = db.query(User).filter(User.username == login_data.username).first()

        if not user:
            return None

        if not self.verify_password(login_data.password, user.password_hash):
            return None

        # Update last login
        user.last_login_at = datetime.utcnow()
        db.commit()

        return user

    async def login(self, login_data: UserLogin, db: Session) -> TokenResponse:
        """Login user and return tokens"""
        user = await self.authenticate_user(login_data, db)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
            )

        # Create tokens
        access_token = self.create_access_token(
            user_id=str(user.id), username=user.username, role=user.role.value
        )

        refresh_token = self.create_refresh_token(user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
            user=UserResponse.from_orm(user),
        )

    async def refresh_access_token(self, refresh_token: str, db: Session) -> TokenResponse:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])

            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
                )

            user_id = payload.get("sub")
            user = db.query(User).filter(User.id == user_id).first()

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled"
                )

            # Create new access token
            access_token = self.create_access_token(
                user_id=str(user.id), username=user.username, role=user.role.value
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,  # Return same refresh token
                expires_in=self.access_token_expire_minutes * 60,
                user=UserResponse.from_orm(user),
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db),
    ) -> User:
        """Get current authenticated user from JWT token"""
        token = credentials.credentials

        token_data = self.verify_token(token)

        user = db.query(User).filter(User.id == token_data.sub).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
            )

        return user

    def require_role(self, *allowed_roles: UserRole):
        """Decorator/dependency to require specific roles"""

        async def role_checker(current_user: User = Depends(self.get_current_user)) -> User:
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
                )
            return current_user

        return role_checker


# Global auth manager instance
auth_manager = AuthManager()

# Convenience functions
hash_password = auth_manager.hash_password
verify_password = auth_manager.verify_password
create_access_token = auth_manager.create_access_token
verify_access_token = auth_manager.verify_token
get_current_user = auth_manager.get_current_user
require_role = auth_manager.require_role


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current admin user"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


import asyncio

# Rate limiting
from collections import defaultdict
from datetime import datetime, timedelta


class RateLimiter:
    """Simple rate limiter"""

    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window
        self.clients = defaultdict(list)
        self._cleanup_task = None

    async def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(seconds=self.window)

        # Clean old requests
        self.clients[client_id] = [
            req_time for req_time in self.clients[client_id] if req_time > minute_ago
        ]

        # Check limit
        if len(self.clients[client_id]) >= self.requests:
            return False

        # Add current request
        self.clients[client_id].append(now)
        return True

    async def cleanup(self):
        """Periodic cleanup of old entries"""
        while True:
            await asyncio.sleep(300)  # Clean every 5 minutes
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=self.window)

            for client_id in list(self.clients.keys()):
                self.clients[client_id] = [
                    req_time for req_time in self.clients[client_id] if req_time > window_start
                ]

                if not self.clients[client_id]:
                    del self.clients[client_id]


# Global rate limiter
rate_limiter = RateLimiter(requests=settings.api.rate_limit, window=60)


async def check_rate_limit(request: Request):
    """FastAPI dependency to check rate limit"""
    client_ip = request.client.host

    if not await rate_limiter.check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
        )

    return True
