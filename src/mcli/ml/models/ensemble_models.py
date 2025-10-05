"""Ensemble models for stock prediction"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from base_models import BaseStockModel, ModelMetrics, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for individual models"""

    model_type: str
    hidden_dims: List[int]
    dropout_rate: float
    learning_rate: float
    weight_decay: float
    batch_size: int
    epochs: int


@dataclass
class EnsembleConfig:
    """Configuration for ensemble model"""

    base_models: List[ModelConfig]
    ensemble_method: str = "weighted_average"  # weighted_average, stacking, voting
    meta_learner_config: Optional[ModelConfig] = None
    feature_subsampling: bool = True
    bootstrap_samples: bool = True
    n_bootstrap: int = 5


class AttentionStockPredictor(BaseStockModel):
    """Attention-based stock predictor"""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 256,
        num_heads: int = 8,
        num_layers: int = 3,
        output_dim: int = 2,
        dropout_rate: float = 0.1,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(input_dim, config)

        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.output_dim = output_dim

        # Input projection
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        # Multi-head attention layers
        self.attention_layers = nn.ModuleList(
            [
                nn.MultiheadAttention(
                    embed_dim=hidden_dim,
                    num_heads=num_heads,
                    dropout=dropout_rate,
                    batch_first=True,
                )
                for _ in range(num_layers)
            ]
        )

        # Feed-forward networks
        self.ffn_layers = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim * 2),
                    nn.ReLU(),
                    nn.Dropout(dropout_rate),
                    nn.Linear(hidden_dim * 2, hidden_dim),
                    nn.Dropout(dropout_rate),
                )
                for _ in range(num_layers)
            ]
        )

        # Layer normalization
        self.layer_norms = nn.ModuleList([nn.LayerNorm(hidden_dim) for _ in range(num_layers * 2)])

        # Output layers
        self.output_layer = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim // 2, output_dim),
        )

        self.softmax = nn.Softmax(dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with attention mechanism"""
        # Project input
        x = self.input_proj(x)

        # Add sequence dimension for attention (treat features as sequence)
        if x.dim() == 2:
            x = x.unsqueeze(1)  # [batch, 1, features]

        # Apply attention layers
        for i in range(self.num_layers):
            # Self-attention
            residual = x
            x = self.layer_norms[i * 2](x)
            attn_output, _ = self.attention_layers[i](x, x, x)
            x = residual + attn_output

            # Feed-forward
            residual = x
            x = self.layer_norms[i * 2 + 1](x)
            ffn_output = self.ffn_layers[i](x)
            x = residual + ffn_output

        # Global pooling and output
        x = x.mean(dim=1)  # Average pooling across sequence
        return self.output_layer(x)

    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        self.eval()
        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            logits = self.forward(X_tensor)
            probas = self.softmax(logits)
            return probas.cpu().numpy()


class TransformerStockModel(BaseStockModel):
    """Transformer model for stock prediction"""

    def __init__(
        self,
        input_dim: int,
        d_model: int = 256,
        nhead: int = 8,
        num_layers: int = 4,
        dim_feedforward: int = 1024,
        output_dim: int = 2,
        dropout_rate: float = 0.1,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(input_dim, config)

        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers

        # Input embedding
        self.input_embedding = nn.Linear(input_dim, d_model)
        self.pos_encoding = PositionalEncoding(d_model, dropout_rate)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout_rate,
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)

        # Output layers
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model // 2, output_dim),
        )

        self.softmax = nn.Softmax(dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through transformer"""
        # Embed input
        x = self.input_embedding(x)

        # Add sequence dimension if needed
        if x.dim() == 2:
            x = x.unsqueeze(1)

        # Add positional encoding
        x = self.pos_encoding(x)

        # Apply transformer
        x = self.transformer_encoder(x)

        # Global average pooling
        x = x.mean(dim=1)

        return self.classifier(x)

    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        self.eval()
        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            logits = self.forward(X_tensor)
            probas = self.softmax(logits)
            return probas.cpu().numpy()


class PositionalEncoding(nn.Module):
    """Positional encoding for transformer"""

    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


class LSTMStockPredictor(BaseStockModel):
    """LSTM-based stock predictor"""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 256,
        num_layers: int = 2,
        output_dim: int = 2,
        dropout_rate: float = 0.2,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(input_dim, config)

        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout_rate if num_layers > 1 else 0,
            batch_first=True,
            bidirectional=True,
        )

        # Output layers
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),  # *2 for bidirectional
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim, output_dim),
        )

        self.softmax = nn.Softmax(dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through LSTM"""
        # Add sequence dimension if needed
        if x.dim() == 2:
            x = x.unsqueeze(1)

        # LSTM forward pass
        lstm_out, (hidden, cell) = self.lstm(x)

        # Use the last output
        x = lstm_out[:, -1, :]

        return self.classifier(x)

    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        self.eval()
        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            logits = self.forward(X_tensor)
            probas = self.softmax(logits)
            return probas.cpu().numpy()


class CNNFeatureExtractor(BaseStockModel):
    """CNN-based feature extractor for tabular data"""

    def __init__(
        self,
        input_dim: int,
        num_filters: int = 64,
        filter_sizes: List[int] = [3, 5, 7],
        output_dim: int = 2,
        dropout_rate: float = 0.3,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(input_dim, config)

        self.num_filters = num_filters
        self.filter_sizes = filter_sizes

        # Reshape layer to create "image-like" structure
        self.feature_reshape_dim = int(np.sqrt(input_dim)) + 1
        if self.feature_reshape_dim**2 < input_dim:
            self.feature_reshape_dim += 1

        # Padding layer to reach perfect square
        self.padding_size = self.feature_reshape_dim**2 - input_dim
        if self.padding_size > 0:
            self.input_padding = nn.ConstantPad1d((0, self.padding_size), 0)
        else:
            self.input_padding = None

        # 1D Convolutions
        self.conv_layers = nn.ModuleList(
            [
                nn.Conv1d(1, num_filters, kernel_size=filter_size, padding=filter_size // 2)
                for filter_size in filter_sizes
            ]
        )

        # Batch normalization
        self.batch_norms = nn.ModuleList([nn.BatchNorm1d(num_filters) for _ in filter_sizes])

        # Global pooling
        self.global_pool = nn.AdaptiveMaxPool1d(1)

        # Final classifier
        total_filters = num_filters * len(filter_sizes)
        self.classifier = nn.Sequential(
            nn.Linear(total_filters, total_filters // 2),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(total_filters // 2, output_dim),
        )

        self.softmax = nn.Softmax(dim=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through CNN"""
        batch_size = x.size(0)

        # Apply padding if needed
        if self.input_padding is not None:
            x = self.input_padding(x)

        # Add channel dimension
        x = x.unsqueeze(1)  # [batch, 1, features]

        # Apply convolutions
        conv_outputs = []
        for conv_layer, batch_norm in zip(self.conv_layers, self.batch_norms):
            conv_out = F.relu(batch_norm(conv_layer(x)))
            pooled = self.global_pool(conv_out).squeeze(-1)
            conv_outputs.append(pooled)

        # Concatenate all conv outputs
        x = torch.cat(conv_outputs, dim=1)

        return self.classifier(x)

    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        self.eval()
        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            logits = self.forward(X_tensor)
            probas = self.softmax(logits)
            return probas.cpu().numpy()


class DeepEnsembleModel(BaseStockModel):
    """Deep ensemble combining multiple models"""

    def __init__(self, input_dim: int, config: EnsembleConfig):
        super().__init__(input_dim, config.__dict__)
        self.ensemble_config = config
        self.models = nn.ModuleList()
        self.model_weights = None

        # Create base models
        for model_config in config.base_models:
            model = self._create_model(model_config, input_dim)
            self.models.append(model)

        # Meta-learner for stacking
        if config.ensemble_method == "stacking" and config.meta_learner_config:
            meta_input_dim = len(config.base_models) * 2  # Each model outputs 2 classes
            self.meta_learner = self._create_model(config.meta_learner_config, meta_input_dim)
        else:
            self.meta_learner = None

        self.softmax = nn.Softmax(dim=1)

    def _create_model(self, model_config: ModelConfig, input_dim: int) -> BaseStockModel:
        """Create individual model based on configuration"""
        if model_config.model_type == "attention":
            return AttentionStockPredictor(
                input_dim=input_dim,
                hidden_dim=model_config.hidden_dims[0],
                dropout_rate=model_config.dropout_rate,
            )
        elif model_config.model_type == "transformer":
            return TransformerStockModel(
                input_dim=input_dim,
                d_model=model_config.hidden_dims[0],
                dropout_rate=model_config.dropout_rate,
            )
        elif model_config.model_type == "lstm":
            return LSTMStockPredictor(
                input_dim=input_dim,
                hidden_dim=model_config.hidden_dims[0],
                dropout_rate=model_config.dropout_rate,
            )
        elif model_config.model_type == "cnn":
            return CNNFeatureExtractor(
                input_dim=input_dim,
                num_filters=model_config.hidden_dims[0],
                dropout_rate=model_config.dropout_rate,
            )
        else:
            # Default to MLP
            from base_models import MLPBaseModel

            return MLPBaseModel(
                input_dim=input_dim,
                hidden_dims=model_config.hidden_dims,
                dropout_rate=model_config.dropout_rate,
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through ensemble"""
        model_outputs = []

        for model in self.models:
            output = model(x)
            model_outputs.append(output)

        # Stack outputs
        stacked_outputs = torch.stack(model_outputs, dim=1)  # [batch, n_models, n_classes]

        if self.ensemble_config.ensemble_method == "weighted_average":
            # Weighted average of predictions
            if self.model_weights is None:
                weights = torch.ones(len(self.models), device=x.device) / len(self.models)
            else:
                weights = self.model_weights.to(x.device)

            weights = weights.view(1, -1, 1)  # [1, n_models, 1]
            ensemble_output = (stacked_outputs * weights).sum(dim=1)

        elif self.ensemble_config.ensemble_method == "voting":
            # Majority voting (using argmax)
            predictions = torch.argmax(stacked_outputs, dim=2)  # [batch, n_models]
            ensemble_pred = torch.mode(predictions, dim=1)[0]  # [batch]
            ensemble_output = F.one_hot(ensemble_pred, num_classes=stacked_outputs.size(2)).float()

        elif self.ensemble_config.ensemble_method == "stacking" and self.meta_learner is not None:
            # Use meta-learner
            meta_input = stacked_outputs.view(stacked_outputs.size(0), -1)  # Flatten
            ensemble_output = self.meta_learner(meta_input)

        else:
            # Default to simple average
            ensemble_output = stacked_outputs.mean(dim=1)

        return ensemble_output

    def predict_proba(self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Predict class probabilities"""
        self.eval()
        with torch.no_grad():
            X_tensor = self.preprocess_input(X)
            logits = self.forward(X_tensor)
            probas = self.softmax(logits)
            return probas.cpu().numpy()

    def set_model_weights(self, weights: List[float]):
        """Set weights for weighted ensemble"""
        self.model_weights = torch.FloatTensor(weights)

    def get_individual_predictions(
        self, X: Union[torch.Tensor, np.ndarray, pd.DataFrame]
    ) -> List[np.ndarray]:
        """Get predictions from individual models"""
        predictions = []
        self.eval()

        for model in self.models:
            with torch.no_grad():
                pred = model.predict_proba(X)
                predictions.append(pred)

        return predictions


class EnsembleTrainer:
    """Trainer for ensemble models"""

    def __init__(self, ensemble_model: DeepEnsembleModel, config: EnsembleConfig):
        self.ensemble_model = ensemble_model
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.ensemble_model.to(self.device)

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> ValidationResult:
        """Train the ensemble model"""
        logger.info("Training ensemble model...")

        # Train individual models first
        individual_results = []
        for i, (model, model_config) in enumerate(
            zip(self.ensemble_model.models, self.config.base_models)
        ):
            logger.info(
                f"Training model {i+1}/{len(self.ensemble_model.models)} ({model_config.model_type})"
            )

            # Create data subsets if enabled
            X_subset, y_subset = self._create_subset(X_train, y_train, model_config)

            # Train individual model
            result = self._train_individual_model(
                model, model_config, X_subset, y_subset, X_val, y_val
            )
            individual_results.append(result)

        # Calculate ensemble weights based on validation performance
        if X_val is not None and y_val is not None:
            self._calculate_ensemble_weights(X_val, y_val)

        # Train meta-learner if using stacking
        if (
            self.config.ensemble_method == "stacking"
            and self.ensemble_model.meta_learner is not None
        ):
            self._train_meta_learner(X_train, y_train, X_val, y_val)

        # Evaluate ensemble
        train_metrics = self._evaluate(X_train, y_train)
        val_metrics = self._evaluate(X_val, y_val) if X_val is not None else None

        return ValidationResult(
            train_metrics=train_metrics,
            val_metrics=val_metrics,
            training_history={"individual_results": individual_results},
        )

    def _create_subset(
        self, X: np.ndarray, y: np.ndarray, model_config: ModelConfig
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create data subset for individual model training"""
        if self.config.bootstrap_samples:
            # Bootstrap sampling
            n_samples = len(X)
            indices = np.random.choice(n_samples, n_samples, replace=True)
            return X[indices], y[indices]
        else:
            return X, y

    def _train_individual_model(
        self,
        model: BaseStockModel,
        model_config: ModelConfig,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray],
        y_val: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        """Train individual model"""
        from torch.utils.data import DataLoader, TensorDataset

        # Convert to tensors
        X_tensor = torch.FloatTensor(X_train).to(self.device)
        y_tensor = torch.LongTensor(y_train).to(self.device)

        # Create data loader
        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=model_config.batch_size, shuffle=True)

        # Setup optimizer and loss
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=model_config.learning_rate,
            weight_decay=model_config.weight_decay,
        )
        criterion = nn.CrossEntropyLoss()

        # Training loop
        model.train()
        train_losses = []

        for epoch in range(model_config.epochs):
            epoch_loss = 0.0
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            avg_loss = epoch_loss / len(loader)
            train_losses.append(avg_loss)

            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}/{model_config.epochs}, Loss: {avg_loss:.4f}")

        model.is_trained = True
        return {"train_losses": train_losses}

    def _calculate_ensemble_weights(self, X_val: np.ndarray, y_val: np.ndarray):
        """Calculate optimal ensemble weights based on validation performance"""
        individual_predictions = self.ensemble_model.get_individual_predictions(X_val)

        # Calculate individual model accuracies
        accuracies = []
        for pred in individual_predictions:
            pred_labels = np.argmax(pred, axis=1)
            accuracy = np.mean(pred_labels == y_val)
            accuracies.append(accuracy)

        # Convert to weights (higher accuracy = higher weight)
        weights = np.array(accuracies)
        weights = weights / weights.sum()  # Normalize

        self.ensemble_model.set_model_weights(weights.tolist())
        logger.info(f"Ensemble weights: {weights}")

    def _train_meta_learner(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray],
        y_val: Optional[np.ndarray],
    ):
        """Train meta-learner for stacking ensemble"""
        # Get predictions from base models
        train_predictions = self.ensemble_model.get_individual_predictions(X_train)
        meta_X_train = np.concatenate(train_predictions, axis=1)

        # Train meta-learner
        meta_config = self.config.meta_learner_config
        result = self._train_individual_model(
            self.ensemble_model.meta_learner, meta_config, meta_X_train, y_train, None, None
        )

        logger.info("Meta-learner training completed")

    def _evaluate(self, X: np.ndarray, y: np.ndarray) -> ModelMetrics:
        """Evaluate ensemble model"""
        if X is None or y is None:
            return ModelMetrics(0, 0, 0, 0, 0)

        predictions = self.ensemble_model.predict(X)
        probabilities = self.ensemble_model.predict_proba(X)

        return self.ensemble_model.calculate_metrics(y, predictions, probabilities)
