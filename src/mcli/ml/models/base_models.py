"""Base classes for ML models"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    """Container for model performance metrics"""

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_return: Optional[float] = None
    win_rate: Optional[float] = None
    avg_gain: Optional[float] = None
    avg_loss: Optional[float] = None

    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary"""
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "auc_roc": self.auc_roc,
            "sharpe_ratio": self.sharpe_ratio or 0.0,
            "max_drawdown": self.max_drawdown or 0.0,
            "total_return": self.total_return or 0.0,
            "win_rate": self.win_rate or 0.0,
            "avg_gain": self.avg_gain or 0.0,
            "avg_loss": self.avg_loss or 0.0,
        }


@dataclass
class ValidationResult:
    """Container for validation results"""

    train_metrics: ModelMetrics
    val_metrics: ModelMetrics
    test_metrics: Optional[ModelMetrics] = None
    feature_importance: Optional[Dict[str, float]] = None
    predictions: Optional[np.ndarray] = None
    true_labels: Optional[np.ndarray] = None
    training_history: Optional[Dict[str, List[float]]] = None


class BaseStockModel(nn.Module, ABC):
    """Abstract base class for all stock prediction models"""

    def __init__(self, input_dim: int, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.input_dim = input_dim
        self.config = config or {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_trained = False
        self.feature_names: Optional[List[str]] = None
        self.scaler = None

    @abstractmethod
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the model"""
        pass

    @abstractmethod
    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        pass

    def predict(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Make binary predictions"""
        probas = self.predict_proba(X)
        return (probas[:, 1] > 0.5).astype(int)

    def preprocess_input(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> torch.Tensor:
        """Preprocess input data for model"""
        if isinstance(X, pd.DataFrame):
            X = X.values

        if isinstance(X, np.ndarray):
            X = torch.FloatTensor(X)

        # Apply scaling if available
        if self.scaler is not None and not isinstance(X, torch.Tensor):
            X = self.scaler.transform(X)
            X = torch.FloatTensor(X)

        return X.to(self.device)

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance scores"""
        # Base implementation returns None
        # Override in specific models that support feature importance
        return None

    def save_model(self, path: str) -> None:
        """Save model state"""
        state = {
            "model_state_dict": self.state_dict(),
            "config": self.config,
            "input_dim": self.input_dim,
            "feature_names": self.feature_names,
            "scaler": self.scaler,
            "is_trained": self.is_trained,
        }
        torch.save(state, path)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: str) -> None:
        """Load model state"""
        state = torch.load(path, map_location=self.device)
        self.load_state_dict(state["model_state_dict"])
        self.config = state["config"]
        self.input_dim = state["input_dim"]
        self.feature_names = state.get("feature_names")
        self.scaler = state.get("scaler")
        self.is_trained = state.get("is_trained", False)
        logger.info(f"Model loaded from {path}")

    def calculate_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray, y_proba: Optional[np.ndarray] = None
    ) -> ModelMetrics:
        """Calculate comprehensive model metrics"""
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        # Basic classification metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average="weighted", zero_division=0)
        recall = recall_score(y_true, y_pred, average="weighted", zero_division=0)
        f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)

        # AUC-ROC
        auc_roc = 0.0
        if y_proba is not None and len(np.unique(y_true)) > 1:
            try:
                if y_proba.ndim > 1 and y_proba.shape[1] > 1:
                    auc_roc = roc_auc_score(y_true, y_proba[:, 1])
                else:
                    auc_roc = roc_auc_score(y_true, y_proba)
            except Exception as e:
                logger.warning(f"Could not calculate AUC-ROC: {e}")

        # Trading-specific metrics (simplified)
        win_rate = np.mean(y_pred == 1) if len(y_pred) > 0 else 0.0

        return ModelMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            auc_roc=auc_roc,
            win_rate=win_rate,
        )

    def to(self, device):
        """Move model to device and update internal device reference"""
        self.device = device
        return super().to(device)


class MLPBaseModel(BaseStockModel):
    """Basic Multi-Layer Perceptron base model"""

    def __init__(
        self,
        input_dim: int,
        hidden_dims: List[int] = [512, 256, 128],
        output_dim: int = 2,
        dropout_rate: float = 0.3,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(input_dim, config)

        self.hidden_dims = hidden_dims
        self.output_dim = output_dim
        self.dropout_rate = dropout_rate

        # Build network layers
        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.extend(
                [
                    nn.Linear(prev_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(dropout_rate),
                ]
            )
            prev_dim = hidden_dim

        # Output layer
        layers.append(nn.Linear(prev_dim, output_dim))

        self.network = nn.Sequential(*layers)
        self.softmax = nn.Softmax(dim=1)

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, module):
        """Initialize model weights"""
        if isinstance(module, nn.Linear):
            torch.nn.init.xavier_uniform_(module.weight)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        return self.network(x)

    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        self.eval()
        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            logits = self.forward(X_tensor)
            probas = self.softmax(logits)
            return probas.cpu().numpy()


class ResidualBlock(nn.Module):
    """Residual block for deeper networks"""

    def __init__(self, dim: int, dropout_rate: float = 0.1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(dim, dim),
            nn.BatchNorm1d(dim),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        identity = x
        out = self.block(x)
        out += identity
        return self.relu(out)


class ResNetModel(BaseStockModel):
    """ResNet-style model for tabular data"""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 256,
        num_blocks: int = 3,
        output_dim: int = 2,
        dropout_rate: float = 0.2,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(input_dim, config)

        self.hidden_dim = hidden_dim
        self.num_blocks = num_blocks
        self.output_dim = output_dim

        # Input projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
        )

        # Residual blocks
        self.blocks = nn.ModuleList(
            [ResidualBlock(hidden_dim, dropout_rate) for _ in range(num_blocks)]
        )

        # Output layer
        self.output_layer = nn.Linear(hidden_dim, output_dim)
        self.softmax = nn.Softmax(dim=1)

        self.apply(self._init_weights)

    def _init_weights(self, module):
        """Initialize weights"""
        if isinstance(module, nn.Linear):
            torch.nn.init.kaiming_normal_(module.weight, mode="fan_out", nonlinearity="relu")
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        x = self.input_proj(x)

        for block in self.blocks:
            x = block(x)

        return self.output_layer(x)

    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        self.eval()
        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            logits = self.forward(X_tensor)
            probas = self.softmax(logits)
            return probas.cpu().numpy()
