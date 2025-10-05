"""Monitoring API routes"""

from fastapi import APIRouter, Depends

from mcli.ml.auth import get_current_active_user
from mcli.ml.database.models import User

router = APIRouter()


@router.get("/drift")
async def get_drift_status(current_user: User = Depends(get_current_active_user)):
    """Get drift monitoring status"""
    return {"drift_detected": False}
