"""Admin API routes"""

from fastapi import APIRouter, Depends

from mcli.ml.auth import get_current_active_user, require_role
from mcli.ml.database.models import User, UserRole

router = APIRouter()


@router.get("/users")
async def list_users(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """List all users"""
    return {"users": []}
