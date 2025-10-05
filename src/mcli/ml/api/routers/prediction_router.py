"""Prediction API routes"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from mcli.ml.api.schemas import BatchPredictionRequest, PredictionRequest, PredictionResponse
from mcli.ml.auth import get_current_active_user
from mcli.ml.cache import cache_set, cached
from mcli.ml.database.models import Model, Prediction, StockData, User
from mcli.ml.database.session import get_db
from mcli.ml.models import get_model_by_id

router = APIRouter()


class PredictionInput(BaseModel):
    ticker: str
    features: dict
    model_id: Optional[UUID] = None
    horizon: int = 1  # Days ahead


@router.post("/predict", response_model=PredictionResponse)
async def create_prediction(
    request: PredictionInput,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new prediction"""

    # Get model (use default if not specified)
    if request.model_id:
        model = db.query(Model).filter(Model.id == request.model_id).first()
        if not model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    else:
        # Get default deployed model
        model = (
            db.query(Model)
            .filter(Model.status == "deployed")
            .order_by(Model.deployed_at.desc())
            .first()
        )

        if not model:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No deployed model available",
            )

    # Load model
    ml_model = await get_model_by_id(str(model.id))

    # Make prediction
    import numpy as np

    features_array = np.array(list(request.features.values())).reshape(1, -1)
    predicted_return = float(ml_model.predict(features_array)[0])

    # Calculate confidence (mock for now)
    confidence_score = 0.75 + np.random.random() * 0.2

    # Save prediction to database
    prediction = Prediction(
        model_id=model.id,
        user_id=current_user.id,
        ticker=request.ticker,
        prediction_date=datetime.utcnow(),
        target_date=datetime.utcnow() + timedelta(days=request.horizon),
        predicted_return=predicted_return,
        confidence_score=confidence_score,
        feature_importance=request.features,
    )

    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    # Cache prediction
    cache_key = f"prediction:{prediction.id}"
    await cache_set(cache_key, prediction, expire=3600)

    # Background task to update stock data
    background_tasks.add_task(update_stock_data, request.ticker, db)

    return PredictionResponse(
        id=prediction.id,
        ticker=prediction.ticker,
        predicted_return=prediction.predicted_return,
        confidence_score=prediction.confidence_score,
        target_date=prediction.target_date,
        model_id=model.id,
        model_name=model.name,
    )


@router.post("/predict/batch", response_model=List[PredictionResponse])
async def create_batch_predictions(
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create predictions for multiple tickers"""
    predictions = []

    for ticker_data in request.tickers:
        pred_input = PredictionInput(
            ticker=ticker_data.ticker,
            features=ticker_data.features,
            model_id=request.model_id,
            horizon=request.horizon,
        )

        pred = await create_prediction(pred_input, background_tasks, current_user, db)
        predictions.append(pred)

    return predictions


@router.get("/", response_model=List[PredictionResponse])
@cached(expire=60)
async def list_predictions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    ticker: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List user's predictions"""
    query = db.query(Prediction).filter(Prediction.user_id == current_user.id)

    if ticker:
        query = query.filter(Prediction.ticker == ticker)

    if start_date:
        query = query.filter(Prediction.prediction_date >= start_date)

    if end_date:
        query = query.filter(Prediction.prediction_date <= end_date)

    predictions = query.order_by(Prediction.prediction_date.desc()).offset(skip).limit(limit).all()

    return [PredictionResponse.from_orm(p) for p in predictions]


@router.get("/{prediction_id}", response_model=PredictionResponse)
@cached(expire=300)
async def get_prediction(
    prediction_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get specific prediction details"""
    prediction = (
        db.query(Prediction)
        .filter(Prediction.id == prediction_id, Prediction.user_id == current_user.id)
        .first()
    )

    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

    return PredictionResponse.from_orm(prediction)


@router.get("/{prediction_id}/outcome")
async def get_prediction_outcome(
    prediction_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get actual outcome of a prediction"""
    prediction = (
        db.query(Prediction)
        .filter(Prediction.id == prediction_id, Prediction.user_id == current_user.id)
        .first()
    )

    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

    # Check if target date has passed
    if prediction.target_date > datetime.utcnow():
        return {
            "status": "pending",
            "message": "Target date has not been reached yet",
            "target_date": prediction.target_date,
        }

    # Get actual return (mock for now)
    actual_return = prediction.predicted_return + np.random.randn() * 0.02

    # Update prediction with actual outcome
    prediction.actual_return = actual_return
    prediction.outcome_date = datetime.utcnow()
    db.commit()

    return {
        "status": "completed",
        "predicted_return": prediction.predicted_return,
        "actual_return": actual_return,
        "error": abs(prediction.predicted_return - actual_return),
        "accuracy": 1 - abs(prediction.predicted_return - actual_return) / abs(actual_return),
    }


@router.get("/recommendations/latest")
@cached(expire=300)
async def get_latest_recommendations(
    limit: int = Query(10, le=50),
    min_confidence: float = Query(0.7, ge=0, le=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get latest stock recommendations"""
    # Get recent predictions with high confidence
    predictions = (
        db.query(Prediction)
        .filter(
            Prediction.confidence_score >= min_confidence,
            Prediction.prediction_date >= datetime.utcnow() - timedelta(days=1),
        )
        .order_by(Prediction.confidence_score.desc(), Prediction.predicted_return.desc())
        .limit(limit)
        .all()
    )

    recommendations = []
    for pred in predictions:
        action = "buy" if pred.predicted_return > 0.02 else "hold"
        if pred.predicted_return < -0.02:
            action = "sell"

        recommendations.append(
            {
                "ticker": pred.ticker,
                "action": action,
                "predicted_return": pred.predicted_return,
                "confidence": pred.confidence_score,
                "target_date": pred.target_date,
            }
        )

    return recommendations


async def update_stock_data(ticker: str, db: Session):
    """Background task to update stock data"""
    # In real implementation, fetch latest stock data
    stock = db.query(StockData).filter(StockData.ticker == ticker).first()
    if stock:
        stock.last_updated = datetime.utcnow()
        db.commit()
