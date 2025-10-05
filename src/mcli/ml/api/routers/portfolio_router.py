"""Portfolio management API routes"""

from fastapi import APIRouter, Depends

from mcli.ml.auth import get_current_active_user
from mcli.ml.database.models import User

router = APIRouter()


@router.get("/")
async def list_portfolios(current_user: User = Depends(get_current_active_user)):
    """List user portfolios"""
    return {"portfolios": []}
