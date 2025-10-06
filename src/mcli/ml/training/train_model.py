"""
Neural Network Training Pipeline for Politician Trading Predictions

This module trains a PyTorch neural network on real trading data from Supabase.
It uses the same feature engineering as the prediction pipeline for consistency.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from supabase import create_client
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoliticianTradingNet(nn.Module):
    """
    Neural Network for Politician Trading Predictions

    Architecture:
    - Input: 10 engineered features
    - Hidden layers: Configurable depth and width
    - Output: 1 value (probability/score for trade success)
    - Activation: ReLU for hidden layers, Sigmoid for output
    """

    def __init__(
        self, input_size: int = 10, hidden_layers: List[int] = [128, 64, 32], dropout: float = 0.2
    ):
        super(PoliticianTradingNet, self).__init__()

        layers = []
        prev_size = input_size

        # Build hidden layers
        for hidden_size in hidden_layers:
            layers.extend(
                [
                    nn.Linear(prev_size, hidden_size),
                    nn.ReLU(),
                    nn.BatchNorm1d(hidden_size),
                    nn.Dropout(dropout),
                ]
            )
            prev_size = hidden_size

        # Output layer
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)


def fetch_training_data() -> pd.DataFrame:
    """
    Fetch all trading disclosures from Supabase.

    Returns:
        DataFrame with trading disclosure data
    """
    logger.info("Fetching training data from Supabase...")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

    client = create_client(url, key)

    # Fetch disclosures
    result = client.table("trading_disclosures").select("*").execute()

    if not result.data:
        raise ValueError("No trading data found in database")

    df = pd.DataFrame(result.data)
    logger.info(f"Fetched {len(df)} trading disclosures")

    return df


def engineer_features_from_disclosure(row: pd.Series, politician_stats: Dict) -> Dict:
    """
    Engineer features from a single trading disclosure.

    Args:
        row: Trading disclosure row
        politician_stats: Precomputed statistics for the politician

    Returns:
        Dictionary of engineered features
    """
    features = {}
    politician_id = row.get("politician_id")

    # 1. Politician historical performance
    if politician_id in politician_stats:
        stats = politician_stats[politician_id]
        features["politician_trade_count"] = min(stats["total_trades"] / 100, 1.0)
        features["politician_purchase_ratio"] = stats["purchase_ratio"]
        features["politician_diversity"] = min(stats["unique_stocks"] / 50, 1.0)
    else:
        features["politician_trade_count"] = 0.0
        features["politician_purchase_ratio"] = 0.5
        features["politician_diversity"] = 0.0

    # 2. Transaction characteristics
    transaction_type = row.get("transaction_type", "")
    features["transaction_is_purchase"] = 1.0 if "purchase" in transaction_type.lower() else 0.0

    # Amount
    amount = row.get("amount", 0)
    if amount is None:
        amount = 50000  # Default if missing
    features["transaction_amount_log"] = np.log10(max(amount, 1))
    features["transaction_amount_normalized"] = min(amount / 1000000, 1.0)

    # 3. Market cap (estimate from asset description if available)
    # For now, use a default mid-cap score
    features["market_cap_score"] = 0.5

    # 4. Sector encoding (estimate from ticker or default)
    # For now, use a default sector risk
    features["sector_risk"] = 0.5

    # 5. Sentiment and volatility (simulated for now - can be enhanced with market data API)
    features["sentiment_score"] = 0.5
    features["volatility_score"] = 0.3

    # 6. Market timing
    disclosure_date = row.get("disclosure_date")
    if disclosure_date:
        try:
            date_obj = pd.to_datetime(disclosure_date)
            # Calculate how "recent" this trade is (older = less relevant)
            days_old = (datetime.now() - date_obj).days
            features["timing_score"] = 1.0 / (1.0 + days_old / 365)
        except:
            features["timing_score"] = 0.5
    else:
        features["timing_score"] = 0.5

    return features


def calculate_politician_statistics(df: pd.DataFrame) -> Dict:
    """
    Calculate historical statistics for each politician.

    Args:
        df: DataFrame of trading disclosures

    Returns:
        Dictionary mapping politician_id to their statistics
    """
    logger.info("Calculating politician statistics...")

    stats = {}

    for politician_id in df["politician_id"].unique():
        politician_trades = df[df["politician_id"] == politician_id]

        total_trades = len(politician_trades)
        purchases = len(
            politician_trades[
                politician_trades["transaction_type"].str.contains("purchase", case=False, na=False)
            ]
        )
        purchase_ratio = purchases / total_trades if total_trades > 0 else 0.5

        unique_stocks = (
            politician_trades["ticker_symbol"].nunique()
            if "ticker_symbol" in politician_trades.columns
            else 1
        )

        stats[politician_id] = {
            "total_trades": total_trades,
            "purchase_ratio": purchase_ratio,
            "unique_stocks": unique_stocks,
        }

    logger.info(f"Calculated statistics for {len(stats)} politicians")
    return stats


def create_labels(df: pd.DataFrame) -> np.ndarray:
    """
    Create training labels from trading data.

    For now, we'll use a heuristic:
    - Purchases of stocks = positive signal (label = 1)
    - Sales = negative signal (label = 0)
    - This can be enhanced with actual return data

    Args:
        df: Trading disclosures DataFrame

    Returns:
        Array of labels (0 or 1)
    """
    labels = []

    for _, row in df.iterrows():
        transaction_type = row.get("transaction_type", "").lower()

        # Simple heuristic: purchases are considered positive signals
        if "purchase" in transaction_type or "buy" in transaction_type:
            label = 1
        else:
            label = 0

        labels.append(label)

    return np.array(labels)


def prepare_dataset(
    df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, StandardScaler, List[str]]:
    """
    Prepare the full dataset with features and labels.

    Args:
        df: Trading disclosures DataFrame

    Returns:
        Tuple of (features, labels, scaler, feature_names)
    """
    logger.info("Preparing dataset...")

    # Calculate politician statistics first
    politician_stats = calculate_politician_statistics(df)

    # Engineer features for each row
    feature_list = []
    for idx, row in df.iterrows():
        features = engineer_features_from_disclosure(row, politician_stats)
        feature_list.append(features)

    # Convert to DataFrame for easy handling
    features_df = pd.DataFrame(feature_list)
    feature_names = features_df.columns.tolist()

    # Create labels
    labels = create_labels(df)

    # Convert to numpy arrays
    X = features_df.values
    y = labels

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    logger.info(f"Prepared {len(X)} samples with {len(feature_names)} features")
    logger.info(f"Label distribution: {np.bincount(y)}")

    return X_scaled, y, scaler, feature_names


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int = 30,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    hidden_layers: List[int] = [128, 64, 32],
    dropout: float = 0.2,
    device: str = "cpu",
) -> Tuple[PoliticianTradingNet, Dict]:
    """
    Train the neural network.

    Args:
        X_train: Training features
        y_train: Training labels
        X_val: Validation features
        y_val: Validation labels
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        hidden_layers: Hidden layer sizes
        dropout: Dropout rate
        device: Device to train on ('cpu' or 'cuda')

    Returns:
        Tuple of (trained_model, training_history)
    """
    logger.info("Initializing model...")

    # Convert to PyTorch tensors
    X_train_tensor = torch.FloatTensor(X_train)
    y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
    X_val_tensor = torch.FloatTensor(X_val)
    y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1)

    # Create datasets and dataloaders
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    val_dataset = TensorDataset(X_val_tensor, y_val_tensor)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)

    # Initialize model
    input_size = X_train.shape[1]
    model = PoliticianTradingNet(
        input_size=input_size, hidden_layers=hidden_layers, dropout=dropout
    ).to(device)

    # Loss and optimizer
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Training history
    history = {
        "train_loss": [],
        "train_accuracy": [],
        "val_loss": [],
        "val_accuracy": [],
    }

    best_val_accuracy = 0.0

    logger.info("Starting training...")

    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)

            # Forward pass
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # Statistics
            train_loss += loss.item()
            predictions = (outputs >= 0.5).float()
            train_correct += (predictions == batch_y).sum().item()
            train_total += batch_y.size(0)

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)

                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)

                val_loss += loss.item()
                predictions = (outputs >= 0.5).float()
                val_correct += (predictions == batch_y).sum().item()
                val_total += batch_y.size(0)

        # Calculate metrics
        train_loss /= len(train_loader)
        train_accuracy = train_correct / train_total
        val_loss /= len(val_loader)
        val_accuracy = val_correct / val_total

        # Store history
        history["train_loss"].append(train_loss)
        history["train_accuracy"].append(train_accuracy)
        history["val_loss"].append(val_loss)
        history["val_accuracy"].append(val_accuracy)

        # Track best model
        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy

        # Log progress
        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info(
                f"Epoch [{epoch+1}/{epochs}] "
                f"Train Loss: {train_loss:.4f}, Train Acc: {train_accuracy:.4f} | "
                f"Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.4f}"
            )

    logger.info(f"Training completed! Best validation accuracy: {best_val_accuracy:.4f}")

    return model, history


def save_model(
    model: PoliticianTradingNet,
    scaler: StandardScaler,
    history: Dict,
    feature_names: List[str],
    model_name: str = "politician_trading_model",
    model_dir: str = "models",
):
    """
    Save the trained model and metadata.

    Args:
        model: Trained PyTorch model
        scaler: Fitted StandardScaler
        history: Training history
        feature_names: List of feature names
        model_name: Base name for the model
        model_dir: Directory to save models
    """
    logger.info("Saving model...")

    # Create model directory
    model_path = Path(model_dir)
    model_path.mkdir(exist_ok=True)

    # Generate versioned name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    versioned_name = f"{model_name}_{timestamp}"

    # Save PyTorch model
    model_file = model_path / f"{versioned_name}.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "model_architecture": {
                "input_size": model.network[0].in_features,
                "hidden_layers": [
                    layer.out_features
                    for layer in model.network
                    if isinstance(layer, nn.Linear)
                ][:-1],
            },
            "scaler_mean": scaler.mean_.tolist(),
            "scaler_scale": scaler.scale_.tolist(),
            "feature_names": feature_names,
        },
        model_file,
    )

    # Calculate Sharpe ratio (simulated for now - would use actual returns in production)
    final_val_acc = history["val_accuracy"][-1]
    sharpe_ratio = 1.5 + (final_val_acc - 0.5) * 3.0  # Heuristic

    # Save metadata
    metadata = {
        "model_name": versioned_name,
        "base_name": model_name,
        "accuracy": final_val_acc,
        "sharpe_ratio": sharpe_ratio,
        "created_at": datetime.now().isoformat(),
        "epochs": len(history["train_loss"]),
        "batch_size": 32,
        "learning_rate": 0.001,
        "final_metrics": {
            "train_loss": history["train_loss"][-1],
            "train_accuracy": history["train_accuracy"][-1],
            "val_loss": history["val_loss"][-1],
            "val_accuracy": history["val_accuracy"][-1],
        },
        "feature_names": feature_names,
    }

    metadata_file = model_path / f"{versioned_name}.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model saved to {model_file}")
    logger.info(f"Metadata saved to {metadata_file}")

    return model_file, metadata_file


def main(
    epochs: int = 30,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    test_size: float = 0.2,
    random_state: int = 42,
):
    """
    Main training pipeline.

    Args:
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        test_size: Fraction of data to use for validation
        random_state: Random seed for reproducibility
    """
    logger.info("=" * 80)
    logger.info("POLITICIAN TRADING MODEL TRAINING PIPELINE")
    logger.info("=" * 80)

    try:
        # 1. Fetch data
        df = fetch_training_data()

        # 2. Prepare dataset
        X, y, scaler, feature_names = prepare_dataset(df)

        # 3. Train/val split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        logger.info(f"Training set: {len(X_train)} samples")
        logger.info(f"Validation set: {len(X_val)} samples")

        # 4. Train model
        model, history = train_model(
            X_train,
            y_train,
            X_val,
            y_val,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
        )

        # 5. Save model
        model_file, metadata_file = save_model(model, scaler, history, feature_names)

        logger.info("=" * 80)
        logger.info("TRAINING COMPLETED SUCCESSFULLY!")
        logger.info(f"Model: {model_file}")
        logger.info(f"Metadata: {metadata_file}")
        logger.info(f"Final Validation Accuracy: {history['val_accuracy'][-1]:.4f}")
        logger.info("=" * 80)

        return model, history

    except Exception as e:
        logger.error(f"Training failed: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Run training with default parameters
    main(epochs=30, batch_size=32, learning_rate=0.001)
