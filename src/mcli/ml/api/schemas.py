"""API request/response schemas"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Model schemas
class ModelCreate(BaseModel):
    name: str
    model_type: str
    framework: str = "pytorch"
    description: Optional[str] = None
    hyperparameters: Dict[str, Any] = {}


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class ModelResponse(BaseModel):
    id: UUID
    name: str
    version: str
    model_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelMetrics(BaseModel):
    model_id: UUID
    train_accuracy: Optional[float]
    val_accuracy: Optional[float]
    test_accuracy: Optional[float]
    train_loss: Optional[float]
    val_loss: Optional[float]
    test_loss: Optional[float]
    additional_metrics: Dict[str, Any]


# Prediction schemas
class PredictionRequest(BaseModel):
    ticker: str
    features: Dict[str, float]
    model_id: Optional[UUID] = None


class BatchPredictionRequest(BaseModel):
    tickers: List[PredictionRequest]
    model_id: Optional[UUID] = None
    horizon: int = 1


class PredictionResponse(BaseModel):
    id: UUID
    ticker: str
    predicted_return: float
    confidence_score: float
    target_date: datetime
    model_id: UUID
    model_name: str

    class Config:
        from_attributes = True
