"""Data API routes"""

from fastapi import APIRouter, Depends

from mcli.ml.auth import get_current_active_user
from mcli.ml.database.models import User

router = APIRouter()


@router.get("/stocks/{ticker}")
async def get_stock_data(ticker: str, current_user: User = Depends(get_current_active_user)):
    """Get stock data"""
    return {"ticker": ticker, "data": {}}
