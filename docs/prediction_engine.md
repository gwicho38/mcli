# Politician Trading Prediction Engine

## Overview

The Prediction Engine analyzes politician trading disclosures to generate stock recommendations with confidence scores and risk assessments.

## How It Works

### Data Analysis

The engine processes trading disclosure data through the following steps:

1. **Filter Recent Trades**: Only analyzes trades from the last 90 days
2. **Group by Ticker**: Aggregates all trades for each stock symbol
3. **Calculate Trading Patterns**: Determines buy/sell ratios
4. **Generate Predictions**: Creates recommendations based on patterns
5. **Score Confidence**: Assigns confidence based on signal quality

### Prediction Algorithm

#### Buy Signal
- **Trigger**: Buy ratio > 70% of total trades
- **Return**: +2% to +15% predicted
- **Risk Score**: 0.3 - 0.6 (lower risk)
- **Example**: If 8 out of 10 trades are purchases

#### Sell Signal
- **Trigger**: Sell ratio > 70% of total trades
- **Return**: -10% to -2% predicted
- **Risk Score**: 0.6 - 0.9 (higher risk)
- **Example**: If 8 out of 10 trades are sales

#### Hold Signal
- **Trigger**: Mixed trading pattern
- **Return**: -2% to +2% predicted
- **Risk Score**: 0.4 - 0.8 (moderate)
- **Example**: 5 buys, 5 sells

### Confidence Scoring

Confidence is calculated using three factors:

1. **Trade Count** (30% weight)
   - More trades = higher confidence
   - Caps at 10 trades for maximum score
   - Formula: `min(trade_count / 10, 1.0)`

2. **Consistency** (40% weight)
   - All buy or all sell = higher confidence
   - Mixed signals = lower confidence
   - Formula: `|buy_ratio - sell_ratio|`

3. **Recency** (30% weight)
   - Recent trades = higher confidence
   - Older trades = lower confidence
   - Formula: `1.0 - (days_ago / 90)`

**Final Confidence**:
```
confidence = (trade_count_score * 0.3) +
             (consistency_score * 0.4) +
             (recency_score * 0.3)
```

Range: 50% - 95%

### Minimum Requirements

- **Minimum Trades**: 2 trades per ticker
- **Time Window**: 90 days
- **Data Quality**: Must have ticker_symbol field

## Usage

### Basic Usage

```python
from mcli.ml.predictions import PoliticianTradingPredictor
import pandas as pd

# Initialize predictor
predictor = PoliticianTradingPredictor()

# Load trading disclosures (from Supabase, CSV, etc.)
disclosures = pd.DataFrame({
    'ticker_symbol': ['AAPL', 'AAPL', 'MSFT'],
    'transaction_type': ['purchase', 'purchase', 'sale'],
    'amount': ['$50,000', '$75,000', '$100,000'],
    'disclosure_date': ['2025-09-15', '2025-09-20', '2025-09-25']
})

# Generate predictions
predictions = predictor.generate_predictions(disclosures)

# View results
print(predictions[['ticker', 'recommendation', 'confidence', 'predicted_return']])
```

### Get Top Picks

```python
# Get top 10 stocks by score (confidence * abs(return))
top_picks = predictor.get_top_picks(predictions, n=10)
```

### Filter by Recommendation

```python
# Get high-confidence buy recommendations
buys = predictor.get_buy_recommendations(predictions, min_confidence=0.7)

# Get high-confidence sell recommendations
sells = predictor.get_sell_recommendations(predictions, min_confidence=0.7)
```

## Output Format

### Prediction DataFrame Columns

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | str | Stock ticker symbol |
| `predicted_return` | float | Expected return (-1.0 to 1.0) |
| `confidence` | float | Prediction confidence (0.5 to 0.95) |
| `risk_score` | float | Risk assessment (0.0 to 1.0) |
| `recommendation` | str | BUY, SELL, or HOLD |
| `trade_count` | int | Total trades for this ticker |
| `buy_count` | int | Number of purchase trades |
| `sell_count` | int | Number of sale trades |
| `signal_strength` | float | Pattern consistency (0.0 to 1.0) |

### Example Output

```
  ticker recommendation  confidence  predicted_return  risk_score  trade_count
0   AAPL            BUY        0.85             0.082        0.35            8
1   MSFT           HOLD        0.62             0.012        0.55            4
2  GOOGL            BUY        0.78             0.065        0.42            6
3   TSLA           SELL        0.71            -0.045        0.68            5
```

## Integration with Dashboard

The prediction engine is automatically used in the ML Dashboard:

### Automatic Integration

```python
# In app_integrated.py
predictor = get_predictor()  # Cached instance
predictions = predictor.generate_predictions(disclosures)
```

### Dashboard Features

1. **Live Predictions Page**
   - Displays current predictions from real trading data
   - Filters by confidence and recommendation
   - Sortable by return, confidence, or risk

2. **Summary Statistics**
   - Total buy/sell signals
   - Average confidence
   - Total trades analyzed

3. **Visual Analysis**
   - Risk-return scatter plots
   - Confidence distribution
   - Recommendation breakdown

## Customization

### Adjust Time Window

```python
predictor = PoliticianTradingPredictor()
predictor.recent_days = 60  # Look at last 60 days instead of 90
```

### Change Minimum Trades

```python
predictor = PoliticianTradingPredictor()
predictor.min_trades_threshold = 5  # Require 5 trades instead of 2
```

### Custom Confidence Weights

Modify the confidence calculation in `_calculate_prediction()`:

```python
confidence = (
    trade_count_score * 0.4 +    # Increase weight on volume
    consistency_score * 0.3 +    # Decrease weight on consistency
    recency_score * 0.3          # Keep recency the same
)
```

## Data Requirements

### Required Fields

- `ticker_symbol`: Stock ticker (e.g., "AAPL", "MSFT")

### Optional Fields (Enhance Predictions)

- `transaction_type`: "purchase", "buy", "sale", "sell"
- `disclosure_date`: Date of disclosure
- `amount`: Transaction amount

### Field Handling

- **Missing `transaction_type`**: Uses trade count only
- **Missing `disclosure_date`**: Uses default recency score
- **Missing `amount`**: Estimates based on trade count

## Performance

### Typical Processing Time

- **100 disclosures**: ~50ms
- **1,000 disclosures**: ~200ms
- **10,000 disclosures**: ~2s

### Optimization Tips

1. **Pre-filter Data**: Remove old disclosures before passing to predictor
2. **Cache Results**: Dashboard caches predictions for 60 seconds
3. **Batch Processing**: Process all tickers together, not individually

## Limitations

### Current Limitations

1. **No Price Data**: Doesn't use actual stock prices
2. **No Market Context**: Doesn't consider market conditions
3. **Simple Pattern Recognition**: Basic buy/sell ratio analysis
4. **No Time Series**: Doesn't model temporal patterns

### Future Enhancements

- [ ] Integrate real-time stock price data
- [ ] Add technical indicators (RSI, MACD, etc.)
- [ ] Machine learning model for pattern recognition
- [ ] Sentiment analysis from disclosure text
- [ ] Portfolio optimization
- [ ] Backtesting framework

## Testing

### Unit Tests

```bash
# Run prediction engine tests
pytest tests/unit/test_prediction_engine.py -v
```

### Integration Tests

```bash
# Test with real data
pytest tests/integration/test_ml_predictions.py -v
```

### Manual Testing

```python
from mcli.ml.predictions import PoliticianTradingPredictor
import pandas as pd

# Create test data
test_data = pd.DataFrame({
    'ticker_symbol': ['AAPL'] * 5 + ['MSFT'] * 3,
    'transaction_type': ['purchase'] * 5 + ['sale'] * 3,
    'disclosure_date': pd.date_range('2025-09-01', periods=8, freq='W')
})

predictor = PoliticianTradingPredictor()
predictions = predictor.generate_predictions(test_data)

# Should show:
# - AAPL as BUY (5 purchases)
# - MSFT as SELL (3 sales)
print(predictions)
```

## Troubleshooting

### No Predictions Generated

**Cause**: Data doesn't meet minimum requirements
**Solution**:
```python
# Check data quality
print(f"Total disclosures: {len(disclosures)}")
print(f"Unique tickers: {disclosures['ticker_symbol'].nunique()}")
print(f"Date range: {disclosures['disclosure_date'].min()} to {disclosures['disclosure_date'].max()}")
```

### Low Confidence Scores

**Cause**: Mixed trading signals or low trade count
**Solution**: This is expected - real trading patterns are often mixed

### Empty DataFrame Returned

**Cause**: No tickers meet minimum trade threshold
**Solution**: Lower `min_trades_threshold` or expand `recent_days`

## API Reference

### PoliticianTradingPredictor

#### Constructor

```python
PoliticianTradingPredictor()
```

No parameters needed. Configuration via instance variables.

#### Methods

##### `generate_predictions(disclosures: pd.DataFrame) -> pd.DataFrame`

Generate predictions from trading disclosures.

**Parameters**:
- `disclosures`: DataFrame with trading data

**Returns**:
- DataFrame with predictions (see Output Format)

##### `get_top_picks(predictions: pd.DataFrame, n: int = 10) -> pd.DataFrame`

Get top N recommendations by score.

**Parameters**:
- `predictions`: Predictions DataFrame
- `n`: Number of top picks (default: 10)

**Returns**:
- Filtered and sorted DataFrame

##### `get_buy_recommendations(predictions: pd.DataFrame, min_confidence: float = 0.6) -> pd.DataFrame`

Filter buy recommendations above confidence threshold.

##### `get_sell_recommendations(predictions: pd.DataFrame, min_confidence: float = 0.6) -> pd.DataFrame`

Filter sell recommendations above confidence threshold.

## Examples

See `examples/prediction_examples.py` for more usage examples.

## Support

- **Documentation**: This file
- **Source Code**: `src/mcli/ml/predictions/prediction_engine.py`
- **Tests**: `tests/unit/test_prediction_engine.py`
- **Issues**: https://github.com/gwicho38/mcli/issues

---

**Version**: 7.1.0
**Last Updated**: October 6, 2025
