"""Stock recommendation models"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from base_models import BaseStockModel, ModelMetrics, ValidationResult
from ensemble_models import DeepEnsembleModel, EnsembleConfig, ModelConfig

logger = logging.getLogger(__name__)


@dataclass
class RecommendationConfig:
    """Configuration for recommendation model"""

    ensemble_config: EnsembleConfig
    risk_adjustment: bool = True
    confidence_threshold: float = 0.6
    diversification_penalty: float = 0.1
    sector_weights: Optional[Dict[str, float]] = None
    max_positions: int = 20
    rebalance_frequency: str = "weekly"  # daily, weekly, monthly


@dataclass
class PortfolioRecommendation:
    """Portfolio recommendation result"""

    ticker: str
    recommendation_score: float
    confidence: float
    risk_level: str
    expected_return: float
    risk_adjusted_score: float
    position_size: float
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    recommendation_reason: str = ""
    key_features: List[str] = None
    warnings: List[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.key_features is None:
            self.key_features = []
        if self.warnings is None:
            self.warnings = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


class StockRecommendationModel(BaseStockModel):
    """Main stock recommendation model combining ensemble prediction with portfolio optimization"""

    def __init__(self, input_dim: int, config: RecommendationConfig):
        super().__init__(input_dim, config.__dict__)
        self.recommendation_config = config

        # Core ensemble model
        self.ensemble_model = DeepEnsembleModel(input_dim, config.ensemble_config)

        # Risk assessment network
        self.risk_network = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 3),  # low, medium, high risk
        )

        # Expected return regression network
        self.return_network = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 1),  # Expected return
        )

        # Confidence estimation network
        self.confidence_network = nn.Sequential(
            nn.Linear(input_dim + 2, 128),  # +2 for prediction and risk
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),  # Confidence between 0 and 1
        )

        self.softmax = nn.Softmax(dim=1)

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass returning multiple outputs"""
        # Main prediction
        main_prediction = self.ensemble_model(x)

        # Risk assessment
        risk_logits = self.risk_network(x)
        risk_probs = self.softmax(risk_logits)

        # Expected return
        expected_returns = self.return_network(x)

        # Confidence estimation
        # Combine main prediction probabilities with risk assessment
        main_probs = self.softmax(main_prediction)
        max_prob = torch.max(main_probs, dim=1, keepdim=True)[0]
        risk_entropy = -torch.sum(risk_probs * torch.log(risk_probs + 1e-8), dim=1, keepdim=True)

        confidence_input = torch.cat([x, max_prob, risk_entropy], dim=1)
        confidence = self.confidence_network(confidence_input)

        return {
            "main_prediction": main_prediction,
            "risk_assessment": risk_probs,
            "expected_returns": expected_returns,
            "confidence": confidence,
        }

    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        self.eval()
        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            outputs = self.forward(X_tensor)
            probas = self.softmax(outputs["main_prediction"])
            return probas.cpu().numpy()

    def generate_recommendations(
        self,
        X: Union[torch.Tensor, np.ndarray, pd.DataFrame],
        tickers: List[str],
        market_data: Optional[pd.DataFrame] = None,
    ) -> List[PortfolioRecommendation]:
        """Generate portfolio recommendations"""
        self.eval()
        recommendations = []

        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            outputs = self.forward(X_tensor)

            # Extract predictions
            main_probs = self.softmax(outputs["main_prediction"]).cpu().numpy()
            risk_probs = outputs["risk_assessment"].cpu().numpy()
            expected_returns = outputs["expected_returns"].cpu().numpy().flatten()
            confidences = outputs["confidence"].cpu().numpy().flatten()

            for i, ticker in enumerate(tickers):
                rec = self._create_recommendation(
                    ticker,
                    main_probs[i],
                    risk_probs[i],
                    expected_returns[i],
                    confidences[i],
                    X_tensor[i].cpu().numpy(),
                    market_data,
                )
                recommendations.append(rec)

        # Apply portfolio-level optimization
        recommendations = self._optimize_portfolio(recommendations)

        return recommendations

    def _create_recommendation(
        self,
        ticker: str,
        main_prob: np.ndarray,
        risk_prob: np.ndarray,
        expected_return: float,
        confidence: float,
        features: np.ndarray,
        market_data: Optional[pd.DataFrame],
    ) -> PortfolioRecommendation:
        """Create individual stock recommendation"""

        # Basic recommendation score (probability of positive outcome)
        recommendation_score = main_prob[1]  # Assuming class 1 is positive

        # Risk level determination
        risk_levels = ["low", "medium", "high"]
        risk_level = risk_levels[np.argmax(risk_prob)]

        # Risk-adjusted score
        risk_penalty = {"low": 0.0, "medium": 0.1, "high": 0.2}
        risk_adjusted_score = recommendation_score * (1 - risk_penalty[risk_level])

        # Position sizing based on confidence and risk
        base_position = 0.05  # 5% base position
        confidence_multiplier = confidence * 2  # Scale confidence
        risk_multiplier = {"low": 1.0, "medium": 0.8, "high": 0.6}

        position_size = base_position * confidence_multiplier * risk_multiplier[risk_level]
        position_size = min(position_size, 0.15)  # Max 15% position

        # Price targets (simplified - would use more sophisticated models in practice)
        entry_price = None
        target_price = None
        stop_loss = None

        if market_data is not None and ticker in market_data["symbol"].values:
            ticker_data = market_data[market_data["symbol"] == ticker].iloc[-1]
            current_price = ticker_data["close"]

            entry_price = current_price
            target_price = current_price * (1 + expected_return * 0.5)  # Conservative target
            stop_loss = current_price * (
                1 - 0.1 * (1 + risk_penalty[risk_level])
            )  # Dynamic stop loss

        # Generate explanation
        reason = self._generate_recommendation_reason(
            recommendation_score, risk_level, confidence, expected_return
        )

        # Key features (simplified - would extract from feature importance)
        key_features = self._extract_key_features(features)

        # Warnings
        warnings = self._generate_warnings(risk_level, confidence, recommendation_score)

        return PortfolioRecommendation(
            ticker=ticker,
            recommendation_score=recommendation_score,
            confidence=confidence,
            risk_level=risk_level,
            expected_return=expected_return,
            risk_adjusted_score=risk_adjusted_score,
            position_size=position_size,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            recommendation_reason=reason,
            key_features=key_features,
            warnings=warnings,
        )

    def _generate_recommendation_reason(
        self, score: float, risk: str, confidence: float, expected_return: float
    ) -> str:
        """Generate human-readable recommendation reason"""
        if score > 0.7:
            strength = "Strong"
        elif score > 0.6:
            strength = "Moderate"
        else:
            strength = "Weak"

        return (
            f"{strength} recommendation based on {confidence:.1%} confidence. "
            f"Expected return: {expected_return:.1%}, Risk level: {risk}."
        )

    def _extract_key_features(self, features: np.ndarray) -> List[str]:
        """Extract key features driving the recommendation"""
        # Simplified implementation - would use feature importance in practice
        return ["technical_indicators", "political_influence", "market_regime"]

    def _generate_warnings(self, risk_level: str, confidence: float, score: float) -> List[str]:
        """Generate warnings for the recommendation"""
        warnings = []

        if confidence < 0.5:
            warnings.append("Low confidence prediction")

        if risk_level == "high":
            warnings.append("High risk investment")

        if score < 0.55:
            warnings.append("Weak recommendation signal")

        return warnings

    def _optimize_portfolio(
        self, recommendations: List[PortfolioRecommendation]
    ) -> List[PortfolioRecommendation]:
        """Apply portfolio-level optimization"""
        # Sort by risk-adjusted score
        recommendations.sort(key=lambda x: x.risk_adjusted_score, reverse=True)

        # Apply position limits
        total_position = 0.0
        max_positions = self.recommendation_config.max_positions

        optimized_recommendations = []
        for i, rec in enumerate(recommendations):
            if i >= max_positions:
                break

            # Adjust position size based on portfolio allocation
            if total_position + rec.position_size > 1.0:
                rec.position_size = max(0, 1.0 - total_position)

            total_position += rec.position_size

            # Only include if meets confidence threshold
            if rec.confidence >= self.recommendation_config.confidence_threshold:
                optimized_recommendations.append(rec)

            if total_position >= 1.0:
                break

        return optimized_recommendations


class RecommendationTrainer:
    """Trainer for recommendation model"""

    def __init__(self, model: StockRecommendationModel, config: RecommendationConfig):
        self.model = model
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        returns_train: np.ndarray,
        risk_labels_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        returns_val: Optional[np.ndarray] = None,
        risk_labels_val: Optional[np.ndarray] = None,
        epochs: int = 100,
        batch_size: int = 64,
    ) -> ValidationResult:
        """Train the recommendation model"""

        from torch.utils.data import DataLoader, TensorDataset

        logger.info("Training recommendation model...")

        # Convert to tensors
        X_tensor = torch.FloatTensor(X_train).to(self.device)
        y_tensor = torch.LongTensor(y_train).to(self.device)
        returns_tensor = torch.FloatTensor(returns_train).to(self.device)
        risk_tensor = torch.LongTensor(risk_labels_train).to(self.device)

        # Create data loader
        dataset = TensorDataset(X_tensor, y_tensor, returns_tensor, risk_tensor)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        # Setup optimizers
        ensemble_params = list(self.model.ensemble_model.parameters())
        other_params = (
            list(self.model.risk_network.parameters())
            + list(self.model.return_network.parameters())
            + list(self.model.confidence_network.parameters())
        )

        ensemble_optimizer = torch.optim.Adam(ensemble_params, lr=0.001, weight_decay=1e-4)
        other_optimizer = torch.optim.Adam(other_params, lr=0.0005, weight_decay=1e-4)

        # Loss functions
        classification_loss = nn.CrossEntropyLoss()
        regression_loss = nn.MSELoss()
        confidence_loss = nn.BCELoss()

        # Training loop
        train_losses = []
        val_losses = []

        for epoch in range(epochs):
            self.model.train()
            epoch_loss = 0.0

            for batch_X, batch_y, batch_returns, batch_risk in loader:
                # Zero gradients
                ensemble_optimizer.zero_grad()
                other_optimizer.zero_grad()

                # Forward pass
                outputs = self.model(batch_X)

                # Calculate losses
                main_loss = classification_loss(outputs["main_prediction"], batch_y)
                risk_loss = classification_loss(outputs["risk_assessment"], batch_risk)
                return_loss = regression_loss(outputs["expected_returns"].squeeze(), batch_returns)

                # Confidence loss (higher confidence for correct predictions)
                main_probs = torch.softmax(outputs["main_prediction"], dim=1)
                correct_probs = main_probs.gather(1, batch_y.unsqueeze(1)).squeeze()
                target_confidence = (correct_probs > 0.5).float()
                conf_loss = confidence_loss(outputs["confidence"].squeeze(), target_confidence)

                # Combined loss
                total_loss = main_loss + 0.5 * risk_loss + 0.3 * return_loss + 0.2 * conf_loss

                # Backward pass
                total_loss.backward()

                # Update parameters
                ensemble_optimizer.step()
                other_optimizer.step()

                epoch_loss += total_loss.item()

            avg_loss = epoch_loss / len(loader)
            train_losses.append(avg_loss)

            # Validation
            if X_val is not None:
                val_loss = self._validate(X_val, y_val, returns_val, risk_labels_val)
                val_losses.append(val_loss)

            if epoch % 10 == 0:
                val_str = f", Val Loss: {val_loss:.4f}" if X_val is not None else ""
                logger.info(f"Epoch {epoch}/{epochs}, Train Loss: {avg_loss:.4f}{val_str}")

        # Final evaluation
        train_metrics = self._evaluate(X_train, y_train)
        val_metrics = self._evaluate(X_val, y_val) if X_val is not None else None

        self.model.is_trained = True

        return ValidationResult(
            train_metrics=train_metrics,
            val_metrics=val_metrics,
            training_history={"train_losses": train_losses, "val_losses": val_losses},
        )

    def _validate(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray,
        returns_val: np.ndarray,
        risk_labels_val: np.ndarray,
    ) -> float:
        """Validate model during training"""
        self.model.eval()

        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_val).to(self.device)
            y_tensor = torch.LongTensor(y_val).to(self.device)
            returns_tensor = torch.FloatTensor(returns_val).to(self.device)
            risk_tensor = torch.LongTensor(risk_labels_val).to(self.device)

            outputs = self.model(X_tensor)

            # Calculate validation loss
            classification_loss = nn.CrossEntropyLoss()
            regression_loss = nn.MSELoss()

            main_loss = classification_loss(outputs["main_prediction"], y_tensor)
            risk_loss = classification_loss(outputs["risk_assessment"], risk_tensor)
            return_loss = regression_loss(outputs["expected_returns"].squeeze(), returns_tensor)

            total_loss = main_loss + 0.5 * risk_loss + 0.3 * return_loss

            return total_loss.item()

    def _evaluate(self, X: np.ndarray, y: np.ndarray) -> ModelMetrics:
        """Evaluate model performance"""
        if X is None or y is None:
            return ModelMetrics(0, 0, 0, 0, 0)

        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)

        return self.model.calculate_metrics(y, predictions, probabilities)
