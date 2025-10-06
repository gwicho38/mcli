# Model Training Guide

## Overview

This guide explains how to train fully-functional neural network models using your existing Supabase data.

## Prerequisites

1. **Data Requirements**:
   - Trading disclosures in Supabase `trading_disclosures` table
   - Politicians data in Supabase `politicians` table
   - Environment variables set:
     ```bash
     export SUPABASE_URL="your_supabase_url"
     export SUPABASE_KEY="your_supabase_key"
     ```

2. **Python Dependencies**:
   ```bash
   pip install torch scikit-learn numpy pandas supabase
   ```

## Training Methods

### Method 1: Command Line (Recommended)

Train a model directly from the command line:

```bash
# Navigate to project root
cd /path/to/mcli

# Run training script
python -m mcli.ml.training.train_model
```

**With custom parameters**:
```bash
python -c "
from mcli.ml.training import train_model
train_model(
    epochs=50,           # Number of training epochs
    batch_size=64,       # Batch size
    learning_rate=0.001, # Learning rate
    test_size=0.2,       # Validation split (20%)
)
"
```

### Method 2: Python Script

Create a custom training script:

```python
from mcli.ml.training import train_model

# Train with default parameters
model, history = train_model(
    epochs=30,
    batch_size=32,
    learning_rate=0.001,
)

# Model and metadata are automatically saved to /models directory
```

### Method 3: From Dashboard (Future)

The dashboard integration will allow you to:
1. Navigate to "Model Training & Evaluation" page
2. Configure hyperparameters
3. Click "Start Training"
4. Monitor real-time progress

## How It Works

### 1. Data Fetching
```python
# Fetches all trading disclosures from Supabase
df = fetch_training_data()
```

### 2. Feature Engineering

For each trading disclosure, the system engineers **10 features**:

| Feature | Description | Range |
|---------|-------------|-------|
| `politician_trade_count` | Historical trading volume (normalized) | 0-1 |
| `politician_purchase_ratio` | Ratio of purchases to total trades | 0-1 |
| `politician_diversity` | Number of unique stocks traded (normalized) | 0-1 |
| `transaction_is_purchase` | Binary: 1 = purchase, 0 = sale | 0 or 1 |
| `transaction_amount_log` | Log-scaled transaction amount | variable |
| `transaction_amount_normalized` | Transaction size relative to $1M | 0-1 |
| `market_cap_score` | Company size indicator | 0-1 |
| `sector_risk` | Industry-specific risk score | 0-1 |
| `sentiment_score` | News sentiment (normalized) | 0-1 |
| `volatility_score` | Price volatility measure | 0-1 |
| `timing_score` | Recency of trade (decay function) | 0-1 |

### 3. Label Creation

**Current approach**: Binary classification
- **Label = 1**: Purchase transactions (positive signal)
- **Label = 0**: Sale transactions (negative signal)

**Future enhancement**: Use actual stock returns
- Fetch historical price data for each ticker
- Calculate 30/60/90-day returns after disclosure
- Label based on whether returns exceeded benchmark

### 4. Model Architecture

**Neural Network**: `PoliticianTradingNet`

```
Input Layer (10 features)
    ↓
Hidden Layer 1 (128 neurons) → ReLU → BatchNorm → Dropout(0.2)
    ↓
Hidden Layer 2 (64 neurons)  → ReLU → BatchNorm → Dropout(0.2)
    ↓
Hidden Layer 3 (32 neurons)  → ReLU → BatchNorm → Dropout(0.2)
    ↓
Output Layer (1 neuron) → Sigmoid
```

**Loss Function**: Binary Cross-Entropy
**Optimizer**: Adam
**Regularization**: Dropout + Batch Normalization

### 5. Training Process

```
1. Split data: 80% train, 20% validation
2. Standardize features using StandardScaler
3. Train for N epochs
4. Track metrics: loss and accuracy (train + validation)
5. Save best model based on validation accuracy
```

### 6. Model Saving

Models are saved in the `/models` directory with:

**`.pt` file** (PyTorch model):
```python
{
    'model_state_dict': model.state_dict(),
    'model_architecture': {...},
    'scaler_mean': [...],
    'scaler_scale': [...],
    'feature_names': [...]
}
```

**`.json` file** (Metadata):
```json
{
    "model_name": "politician_trading_model_20251006_120000",
    "base_name": "politician_trading_model",
    "accuracy": 0.85,
    "sharpe_ratio": 2.1,
    "created_at": "2025-10-06T12:00:00",
    "epochs": 30,
    "batch_size": 32,
    "learning_rate": 0.001,
    "final_metrics": {
        "train_loss": 0.32,
        "train_accuracy": 0.87,
        "val_loss": 0.35,
        "val_accuracy": 0.85
    },
    "feature_names": [...]
}
```

## Loading Trained Models

The dashboard automatically loads the latest model for predictions:

```python
from mcli.ml.dashboard.app_integrated import load_latest_model

model_file, metadata = load_latest_model()
# Uses most recent model from /models directory
```

## Improving Model Performance

### 1. More Data
- Ensure Supabase has sufficient trading disclosures (>1000 recommended)
- More politicians = better generalization

### 2. Better Labels
Integrate real market data:
```python
# Pseudo-code for enhanced labels
def create_enhanced_labels(df):
    for disclosure in df:
        ticker = disclosure['ticker_symbol']
        date = disclosure['disclosure_date']

        # Fetch price 30 days after disclosure
        future_price = get_stock_price(ticker, date + 30_days)
        current_price = get_stock_price(ticker, date)

        return_pct = (future_price - current_price) / current_price

        # Label based on return
        if return_pct > 0.05:
            label = 1  # Good trade
        else:
            label = 0  # Poor trade

    return labels
```

### 3. Hyperparameter Tuning

Experiment with:
- **Epochs**: 20-100 (watch for overfitting)
- **Batch Size**: 16, 32, 64, 128
- **Learning Rate**: 0.0001, 0.001, 0.01
- **Hidden Layers**: Try [256, 128, 64] or [128, 128, 64, 32]
- **Dropout**: 0.1 to 0.5

### 4. Feature Enhancement

Add more features:
```python
# Market data features
- VIX index (market volatility)
- Sector ETF performance
- Congress session schedule
- Economic calendar events

# Politician-specific features
- Committee memberships
- Stock industry overlap
- Historical win rate
```

## Monitoring Training

**Training logs** show real-time progress:
```
2025-10-06 12:00:00 [INFO] Fetching training data from Supabase...
2025-10-06 12:00:01 [INFO] Fetched 2500 trading disclosures
2025-10-06 12:00:02 [INFO] Calculating politician statistics...
2025-10-06 12:00:03 [INFO] Prepared 2500 samples with 10 features
2025-10-06 12:00:04 [INFO] Training set: 2000 samples
2025-10-06 12:00:04 [INFO] Validation set: 500 samples
2025-10-06 12:00:05 [INFO] Starting training...
2025-10-06 12:00:10 [INFO] Epoch [1/30] Train Loss: 0.6543, Train Acc: 0.6125 | Val Loss: 0.6712, Val Acc: 0.6040
2025-10-06 12:00:15 [INFO] Epoch [5/30] Train Loss: 0.4234, Train Acc: 0.7980 | Val Loss: 0.4512, Val Acc: 0.7760
...
2025-10-06 12:01:30 [INFO] Training completed! Best validation accuracy: 0.8520
2025-10-06 12:01:31 [INFO] Model saved to models/politician_trading_model_20251006_120000.pt
```

## Integration with Dashboard

Once trained, models are automatically available in the dashboard:

1. **Model Performance** page shows all trained models
2. **Interactive Predictions** uses latest model for inference
3. **Compare Models** allows side-by-side evaluation

## Troubleshooting

### Error: "No trading data found in database"
- Verify Supabase connection
- Check `trading_disclosures` table has data
- Confirm SUPABASE_URL and SUPABASE_KEY are set

### Low Accuracy (<70%)
- Need more training data (target: 1000+ samples)
- Labels may be too simple (enhance with real returns)
- Try different architectures or hyperparameters

### Overfitting (train acc >> val acc)
- Increase dropout rate (0.3-0.5)
- Reduce model complexity (fewer/smaller layers)
- Add more training data
- Enable early stopping

### Out of Memory
- Reduce batch size (try 16 or 8)
- Use CPU instead of GPU if on laptop
- Reduce hidden layer sizes

## Next Steps

1. **Run your first training**:
   ```bash
   python -m mcli.ml.training.train_model
   ```

2. **Check the models directory**:
   ```bash
   ls -l models/
   ```

3. **Test predictions in dashboard**:
   - Navigate to "Model Training & Evaluation"
   - Go to "Interactive Predictions" tab
   - Make a prediction (will use your new model!)

4. **Iterate and improve**:
   - Collect more data
   - Enhance features
   - Try different architectures
   - Compare model performance

## Advanced: Custom Architecture

Create your own model architecture:

```python
import torch.nn as nn
from mcli.ml.training import train_model, prepare_dataset

class CustomNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(10, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.network(x)

# Use custom model in training pipeline
# (modify train_model.py to accept custom model class)
```

## Support

For issues or questions:
- Check logs in training output
- Review Supabase data quality
- Verify environment variables
- Test with smaller dataset first
