"""ML Models for Stock Recommendation System."""

from typing import Any, Dict

import torch

from .base_models import BaseStockModel, ModelMetrics, ValidationResult
from .ensemble_models import (
    AttentionStockPredictor,
    CNNFeatureExtractor,
    DeepEnsembleModel,
    EnsembleConfig,
    EnsembleTrainer,
    LSTMStockPredictor,
    ModelConfig,
    TransformerStockModel,
)
from .recommendation_models import (
    RecommendationConfig,
    RecommendationTrainer,
    StockRecommendationModel,
)

# Model registry
_loaded_models: Dict[str, Any] = {}


async def load_production_models():
    """Load production models into memory."""
    from mcli.ml.config import settings
    from mcli.ml.logging import get_logger

    logger = get_logger(__name__)
    model_dir = settings.model.model_dir

    if not model_dir.exists():
        model_dir.mkdir(parents=True, exist_ok=True)
        return

    for model_path in model_dir.glob("*.pt"):
        try:
            model_id = model_path.stem
            model = torch.load(model_path, map_location=settings.model.device)
            _loaded_models[model_id] = model
            logger.info(f"Loaded model: {model_id}")
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")


async def get_model_by_id(model_id: str):
    """Get loaded model by ID."""
    from mcli.ml.config import settings

    if model_id not in _loaded_models:
        # Try to load from disk
        model_path = settings.model.model_dir / f"{model_id}.pt"
        if model_path.exists():
            _loaded_models[model_id] = torch.load(model_path, map_location=settings.model.device)

    return _loaded_models.get(model_id)


def initialize_models():
    """Initialize models on startup."""
    from mcli.ml.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Initializing ML models...")


__all__ = [
    "DeepEnsembleModel",
    "AttentionStockPredictor",
    "TransformerStockModel",
    "LSTMStockPredictor",
    "CNNFeatureExtractor",
    "EnsembleTrainer",
    "ModelConfig",
    "EnsembleConfig",
    "BaseStockModel",
    "ModelMetrics",
    "ValidationResult",
    "StockRecommendationModel",
    "RecommendationTrainer",
    "RecommendationConfig",
    "load_production_models",
    "get_model_by_id",
    "initialize_models",
]
