"""Celery background tasks for ML system"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict

from celery import Celery, Task
from celery.schedules import crontab

from mcli.ml.config import settings
from mcli.ml.logging import get_logger

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "mcli_ml", broker=settings.redis.url, backend=settings.redis.url, include=["mcli.ml.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    "update-stock-data": {
        "task": "mcli.ml.tasks.update_stock_data_task",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "retrain-models": {
        "task": "mcli.ml.tasks.retrain_models_task",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "check-model-drift": {
        "task": "mcli.ml.tasks.check_model_drift_task",
        "schedule": crontab(minute=0),  # Every hour
    },
    "cleanup-old-predictions": {
        "task": "mcli.ml.tasks.cleanup_predictions_task",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "generate-daily-report": {
        "task": "mcli.ml.tasks.generate_daily_report_task",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
    },
    "fetch-politician-trades": {
        "task": "mcli.ml.tasks.fetch_politician_trades_task",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
}


class MLTask(Task):
    """Base task with error handling"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure"""
        logger.error(f"Task {self.name} failed: {exc}", exc_info=True)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Log task retry"""
        logger.warning(f"Task {self.name} retrying: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Log task success"""
        logger.info(f"Task {self.name} completed successfully")


@celery_app.task(base=MLTask, bind=True, max_retries=3)
def train_model_task(self, model_id: str, retrain: bool = False) -> Dict[str, Any]:
    """Train or retrain a model"""
    try:
        logger.info(f"Starting training for model {model_id}")

        from mcli.ml.database.models import Model, ModelStatus
        from mcli.ml.database.session import SessionLocal
        from mcli.ml.mlops.pipeline_orchestrator import MLPipeline, PipelineConfig

        # Get model from database
        db = SessionLocal()
        model = db.query(Model).filter(Model.id == model_id).first()

        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Update status
        model.status = ModelStatus.TRAINING
        db.commit()

        # Configure and run pipeline
        config = PipelineConfig(experiment_name=f"model_{model_id}", enable_mlflow=True)

        pipeline = MLPipeline(config)

        # Run training asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(pipeline.run_async())

        # Update model with results
        model.status = ModelStatus.TRAINED
        model.train_accuracy = result.get("train_accuracy")
        model.val_accuracy = result.get("val_accuracy")
        model.test_accuracy = result.get("test_accuracy")
        model.metrics = result

        db.commit()
        db.close()

        logger.info(f"Training completed for model {model_id}")
        return {"model_id": model_id, "status": "completed", "metrics": result}

    except Exception as e:
        logger.error(f"Training failed for model {model_id}: {e}")
        self.retry(countdown=60, exc=e)


@celery_app.task(base=MLTask, bind=True)
def update_stock_data_task(self, ticker: str = None) -> Dict[str, Any]:
    """Update stock data from external APIs"""
    try:
        logger.info(f"Updating stock data{f' for {ticker}' if ticker else ''}")

        from mcli.ml.data_ingestion.api_connectors import YahooFinanceConnector
        from mcli.ml.database.models import StockData
        from mcli.ml.database.session import SessionLocal

        connector = YahooFinanceConnector()
        db = SessionLocal()

        if ticker:
            tickers = [ticker]
        else:
            # Get all tracked tickers
            tickers = db.query(StockData.ticker).distinct().limit(100).all()
            tickers = [t[0] for t in tickers]

        updated_count = 0
        for ticker in tickers:
            try:
                # Fetch latest data
                data = asyncio.run(connector.fetch_stock_data(ticker))

                # Update database
                stock = db.query(StockData).filter(StockData.ticker == ticker).first()
                if not stock:
                    stock = StockData(ticker=ticker)
                    db.add(stock)

                stock.current_price = data.get("price")
                stock.volume = data.get("volume")
                stock.change_1d = data.get("change_1d")
                stock.last_updated = datetime.utcnow()

                updated_count += 1

            except Exception as e:
                logger.error(f"Failed to update {ticker}: {e}")

        db.commit()
        db.close()

        logger.info(f"Updated {updated_count} stocks")
        return {"updated": updated_count, "total": len(tickers)}

    except Exception as e:
        logger.error(f"Stock data update failed: {e}")
        raise


@celery_app.task(base=MLTask)
def check_model_drift_task() -> Dict[str, Any]:
    """Check for model drift"""
    try:
        logger.info("Checking for model drift")

        from mcli.ml.database.models import Model, ModelStatus
        from mcli.ml.database.session import SessionLocal
        from mcli.ml.monitoring.drift_detection import ModelMonitor

        db = SessionLocal()
        deployed_models = db.query(Model).filter(Model.status == ModelStatus.DEPLOYED).all()

        drift_detected = []
        for model in deployed_models:
            monitor = ModelMonitor(str(model.id))

            # Check drift (simplified)
            if monitor.check_drift():
                drift_detected.append(str(model.id))
                logger.warning(f"Drift detected in model {model.id}")

        db.close()

        return {
            "checked": len(deployed_models),
            "drift_detected": len(drift_detected),
            "models_with_drift": drift_detected,
        }

    except Exception as e:
        logger.error(f"Drift check failed: {e}")
        raise


@celery_app.task(base=MLTask)
def cleanup_predictions_task() -> Dict[str, Any]:
    """Clean up old predictions"""
    try:
        logger.info("Cleaning up old predictions")

        from mcli.ml.database.models import Prediction
        from mcli.ml.database.session import SessionLocal

        db = SessionLocal()

        # Delete predictions older than 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        deleted = db.query(Prediction).filter(Prediction.created_at < cutoff_date).delete()

        db.commit()
        db.close()

        logger.info(f"Deleted {deleted} old predictions")
        return {"deleted": deleted}

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


@celery_app.task(base=MLTask)
def retrain_models_task() -> Dict[str, Any]:
    """Retrain models on schedule"""
    try:
        logger.info("Starting scheduled model retraining")

        from mcli.ml.database.models import Model, ModelStatus
        from mcli.ml.database.session import SessionLocal

        db = SessionLocal()

        # Get models that need retraining
        models_to_retrain = (
            db.query(Model)
            .filter(
                Model.status == ModelStatus.DEPLOYED,
                Model.updated_at < datetime.utcnow() - timedelta(days=7),
            )
            .all()
        )

        retrained = []
        for model in models_to_retrain:
            # Trigger retraining
            train_model_task.delay(str(model.id), retrain=True)
            retrained.append(str(model.id))

        db.close()

        logger.info(f"Triggered retraining for {len(retrained)} models")
        return {"retrained": retrained}

    except Exception as e:
        logger.error(f"Retraining failed: {e}")
        raise


@celery_app.task(base=MLTask)
def generate_daily_report_task() -> Dict[str, Any]:
    """Generate daily performance report"""
    try:
        logger.info("Generating daily report")

        from mcli.ml.database.models import Portfolio, Prediction, User
        from mcli.ml.database.session import SessionLocal

        db = SessionLocal()

        # Gather statistics
        total_predictions = (
            db.query(Prediction)
            .filter(Prediction.prediction_date >= datetime.utcnow() - timedelta(days=1))
            .count()
        )

        active_portfolios = db.query(Portfolio).filter(Portfolio.is_active == True).count()

        active_users = (
            db.query(User)
            .filter(User.last_login_at >= datetime.utcnow() - timedelta(days=1))
            .count()
        )

        db.close()

        report = {
            "date": datetime.utcnow().date().isoformat(),
            "predictions_24h": total_predictions,
            "active_portfolios": active_portfolios,
            "active_users_24h": active_users,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # In real implementation, send email or save to storage
        logger.info(f"Daily report generated: {report}")

        return report

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise


@celery_app.task(base=MLTask)
def fetch_politician_trades_task() -> Dict[str, Any]:
    """Fetch latest politician trades"""
    try:
        logger.info("Fetching politician trades")

        from mcli.ml.data_ingestion.api_connectors import CongressionalTradingConnector
        from mcli.ml.database.models import Politician, Trade
        from mcli.ml.database.session import SessionLocal

        connector = CongressionalTradingConnector()
        db = SessionLocal()

        # Fetch recent trades
        trades_data = asyncio.run(connector.fetch_recent_trades())

        new_trades = 0
        for trade_info in trades_data:
            # Check if trade exists
            existing = (
                db.query(Trade)
                .filter(
                    Trade.politician_id == trade_info["politician_id"],
                    Trade.ticker == trade_info["ticker"],
                    Trade.disclosure_date == trade_info["disclosure_date"],
                )
                .first()
            )

            if not existing:
                trade = Trade(**trade_info)
                db.add(trade)
                new_trades += 1

        db.commit()
        db.close()

        logger.info(f"Added {new_trades} new politician trades")
        return {"new_trades": new_trades, "total_processed": len(trades_data)}

    except Exception as e:
        logger.error(f"Failed to fetch politician trades: {e}")
        raise


@celery_app.task(base=MLTask, bind=True)
def process_batch_predictions_task(self, predictions: list) -> Dict[str, Any]:
    """Process batch predictions asynchronously"""
    try:
        logger.info(f"Processing batch of {len(predictions)} predictions")

        import numpy as np

        from mcli.ml.models import get_model_by_id

        results = []
        for pred in predictions:
            model = asyncio.run(get_model_by_id(pred["model_id"]))
            features = np.array(pred["features"]).reshape(1, -1)
            result = model.predict(features)
            results.append({"ticker": pred["ticker"], "prediction": float(result[0])})

        logger.info(f"Batch predictions completed")
        return {"predictions": results}

    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        self.retry(countdown=30, exc=e)


# Worker health check
@celery_app.task(name="health_check")
def health_check():
    """Health check for Celery worker"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
