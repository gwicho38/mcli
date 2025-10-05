"""Populate database with sample data for dashboard testing."""

import asyncio
import random
from datetime import datetime, timedelta

import numpy as np

from mcli.ml.config import settings
from mcli.ml.database.models import (
    BacktestResult,
    Model,
    ModelStatus,
    Portfolio,
    Prediction,
    StockData,
    Trade,
    User,
)
from mcli.ml.database.session import SessionLocal, init_db


def populate_sample_data():
    """Populate database with sample data."""

    # Initialize database
    init_db()

    db = SessionLocal()

    try:
        # Clear existing data (optional)
        print("Clearing existing data...")
        db.query(Prediction).delete()
        db.query(Trade).delete()
        db.query(BacktestResult).delete()
        db.query(Portfolio).delete()
        db.query(Model).delete()
        db.query(User).delete()
        db.query(StockData).delete()
        db.commit()

        # Create sample users
        print("Creating sample users...")
        users = []
        for i in range(5):
            user = User(
                username=f"user_{i+1}",
                email=f"user{i+1}@example.com",
                role="user" if i > 0 else "admin",
                is_active=True,
                last_login_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            )
            users.append(user)
            db.add(user)

        db.commit()

        # Create sample models
        print("Creating sample models...")
        models = []
        model_names = [
            "LSTM Predictor",
            "Transformer Model",
            "Ensemble Model",
            "CNN Extractor",
            "Attention Model",
        ]
        for i, name in enumerate(model_names):
            model = Model(
                name=name,
                version=f"v1.{i}",
                model_type="pytorch",
                status=ModelStatus.DEPLOYED if i < 3 else ModelStatus.TRAINING,
                test_accuracy=random.uniform(0.65, 0.95),
                test_sharpe_ratio=random.uniform(1.2, 2.5),
                test_max_drawdown=random.uniform(0.05, 0.15),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                updated_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                created_by_id=random.choice(users).id,
            )
            models.append(model)
            db.add(model)

        db.commit()

        # Create sample portfolios
        print("Creating sample portfolios...")
        portfolios = []
        portfolio_names = [
            "Growth Portfolio",
            "Value Portfolio",
            "AI Picks",
            "Risk Parity",
            "Momentum Strategy",
        ]
        for i, name in enumerate(portfolio_names):
            portfolio = Portfolio(
                name=name,
                description=f"Strategy based on {name.lower()}",
                initial_capital=100000,
                current_value=100000 * random.uniform(0.9, 1.3),
                total_return=random.uniform(-0.1, 0.3),
                sharpe_ratio=random.uniform(0.8, 2.0),
                max_drawdown=random.uniform(0.05, 0.20),
                is_active=i < 4,
                created_by_id=random.choice(users).id,
            )
            portfolios.append(portfolio)
            db.add(portfolio)

        db.commit()

        # Create sample predictions
        print("Creating sample predictions...")
        tickers = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META", "AMZN", "SPY", "QQQ", "DIA"]

        for _ in range(100):
            prediction = Prediction(
                ticker=random.choice(tickers),
                prediction_date=datetime.utcnow().date() - timedelta(days=random.randint(0, 7)),
                target_date=datetime.utcnow().date() + timedelta(days=random.randint(1, 30)),
                predicted_return=random.uniform(-0.05, 0.05),
                confidence_score=random.uniform(0.5, 0.95),
                model_id=random.choice(models).id,
            )
            db.add(prediction)

        # Add some predictions for today
        for ticker in tickers[:5]:
            prediction = Prediction(
                ticker=ticker,
                prediction_date=datetime.utcnow().date(),
                target_date=datetime.utcnow().date() + timedelta(days=7),
                predicted_return=random.uniform(-0.03, 0.03),
                confidence_score=random.uniform(0.6, 0.9),
                model_id=random.choice(models).id,
            )
            db.add(prediction)

        db.commit()

        # Create sample stock data
        print("Creating sample stock data...")
        for ticker in tickers:
            base_price = random.uniform(50, 500)
            for i in range(30):
                date = datetime.utcnow().date() - timedelta(days=i)
                stock_data = StockData(
                    ticker=ticker,
                    date=date,
                    open=base_price * random.uniform(0.98, 1.02),
                    high=base_price * random.uniform(1.01, 1.03),
                    low=base_price * random.uniform(0.97, 0.99),
                    close=base_price * random.uniform(0.98, 1.02),
                    volume=random.randint(1000000, 50000000),
                    adjusted_close=base_price * random.uniform(0.98, 1.02),
                )
                db.add(stock_data)
                base_price = stock_data.close  # Random walk

        db.commit()

        # Create sample trades
        print("Creating sample trades...")
        for portfolio in portfolios:
            if portfolio.is_active:
                for _ in range(random.randint(5, 15)):
                    trade = Trade(
                        portfolio_id=portfolio.id,
                        ticker=random.choice(tickers),
                        trade_type=random.choice(["buy", "sell"]),
                        quantity=random.randint(10, 100),
                        price=random.uniform(50, 500),
                        executed_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                    )
                    db.add(trade)

        db.commit()

        # Create sample backtest results
        print("Creating sample backtest results...")
        for model in models:
            if model.status == ModelStatus.DEPLOYED:
                backtest = BacktestResult(
                    model_id=model.id,
                    start_date=datetime.utcnow().date() - timedelta(days=180),
                    end_date=datetime.utcnow().date() - timedelta(days=1),
                    initial_capital=100000,
                    final_capital=100000 * random.uniform(0.9, 1.4),
                    total_return=random.uniform(-0.1, 0.4),
                    sharpe_ratio=random.uniform(0.5, 2.5),
                    max_drawdown=random.uniform(0.05, 0.25),
                    win_rate=random.uniform(0.45, 0.65),
                    profit_factor=random.uniform(0.9, 2.0),
                    total_trades=random.randint(50, 200),
                )
                db.add(backtest)

        db.commit()

        print("✅ Sample data populated successfully!")
        print(f"   Users: {len(users)}")
        print(f"   Models: {len(models)}")
        print(f"   Portfolios: {len(portfolios)}")
        print(f"   Predictions: {db.query(Prediction).count()}")
        print(f"   Stock Data: {db.query(StockData).count()}")
        print(f"   Trades: {db.query(Trade).count()}")
        print(f"   Backtest Results: {db.query(BacktestResult).count()}")

    except Exception as e:
        print(f"❌ Error populating data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_sample_data()
