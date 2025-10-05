"""Backtesting API routes"""

from fastapi import APIRouter, Depends

from mcli.ml.auth import get_current_active_user
from mcli.ml.database.models import User

router = APIRouter()


@router.post("/run")
async def run_backtest(current_user: User = Depends(get_current_active_user)):
    """Run backtest"""
    return {"status": "started"}
