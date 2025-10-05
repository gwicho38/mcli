"""Trading API routes"""

from fastapi import APIRouter, Depends

from mcli.ml.auth import get_current_active_user
from mcli.ml.database.models import User

router = APIRouter()


@router.get("/politician/{politician_id}")
async def get_politician_trades(
    politician_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get politician trades"""
    return {"politician_id": politician_id, "trades": []}
