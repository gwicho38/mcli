"""ML Data Pipeline Integration"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from mcli.lib.services.data_pipeline import DataPipelineConfig, LSHDataPipeline
from mcli.lib.services.lsh_client import LSHClient
from mcli.ml.configs.mlops_manager import get_mlops_manager

from .politician_trading_preprocessor import (
    PoliticianTradingPreprocessor,
    PreprocessingConfig,
    PreprocessingResults,
)

logger = logging.getLogger(__name__)


@dataclass
class MLDataPipelineConfig:
    """Configuration for ML data pipeline"""

    # Data ingestion
    batch_size: int = 50
    batch_timeout: int = 60  # seconds
    max_buffer_size: int = 1000

    # Preprocessing
    preprocessing_config: Optional[PreprocessingConfig] = None
    auto_retrain_threshold: int = 100  # New records needed to trigger retraining

    # Storage
    processed_data_dir: Path = Path("./data/ml_ready")
    model_training_data_dir: Path = Path("./data/training")

    # MLOps integration
    enable_mlflow_logging: bool = True
    experiment_name: str = "politician_trading_preprocessing"

    def __post_init__(self):
        if self.preprocessing_config is None:
            self.preprocessing_config = PreprocessingConfig()

        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        self.model_training_data_dir.mkdir(parents=True, exist_ok=True)


class MLDataPipeline:
    """ML-focused data pipeline for politician trading data"""

    def __init__(self, lsh_client: LSHClient, config: Optional[MLDataPipelineConfig] = None):
        self.lsh_client = lsh_client
        self.config = config or MLDataPipelineConfig()

        # Initialize components
        self.base_pipeline = LSHDataPipeline(lsh_client, DataPipelineConfig())
        self.preprocessor = PoliticianTradingPreprocessor(self.config.preprocessing_config)
        self.mlops_manager = get_mlops_manager()

        # Data buffers
        self.raw_data_buffer: List[Dict[str, Any]] = []
        self.processed_data_buffer: List[Dict[str, Any]] = []

        # State tracking
        self._is_running = False
        self._last_preprocessing_time = None
        self._total_records_processed = 0

        # Setup event handlers
        self._setup_ml_handlers()

    def _setup_ml_handlers(self):
        """Setup ML-specific event handlers"""
        self.lsh_client.on("trading.data.received", self._handle_trading_data_for_ml)
        self.lsh_client.on("politician.data.updated", self._handle_politician_update)
        self.lsh_client.on("market.data.sync", self._handle_market_data)

    async def start(self):
        """Start the ML data pipeline"""
        if self._is_running:
            logger.warning("ML pipeline already running")
            return

        logger.info("Starting ML data pipeline")
        self._is_running = True

        # Setup MLOps infrastructure
        self.mlops_manager.setup()

        if self.config.enable_mlflow_logging:
            # Start MLflow experiment
            self.mlops_manager.start_experiment_run(
                run_name=f"preprocessing_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                tags={"component": "data_preprocessing", "pipeline_version": "1.0.0"},
                description="Politician trading data preprocessing pipeline",
            )

        # Start base pipeline
        await self.base_pipeline.start()

        # Start periodic processing
        asyncio.create_task(self._periodic_processing())

    async def stop(self):
        """Stop the ML data pipeline"""
        if not self._is_running:
            return

        logger.info("Stopping ML data pipeline")
        self._is_running = False

        # Process any remaining data
        await self._process_accumulated_data()

        # Stop base pipeline
        await self.base_pipeline.stop()

        # End MLflow run
        if self.config.enable_mlflow_logging:
            self.mlops_manager.end_run()

    async def _handle_trading_data_for_ml(self, event_data: Dict[str, Any]):
        """Handle trading data for ML processing"""
        records = event_data.get("records", [])

        if not records:
            return

        logger.info(f"Received {len(records)} trading records for ML processing")

        # Add to buffer
        self.raw_data_buffer.extend(records)

        # Check if we should process
        if (
            len(self.raw_data_buffer) >= self.config.batch_size
            or len(self.raw_data_buffer) >= self.config.max_buffer_size
        ):
            await self._process_accumulated_data()

    async def _handle_politician_update(self, event_data: Dict[str, Any]):
        """Handle politician metadata updates"""
        politician_data = event_data.get("politician", {})
        logger.info(f"Received politician update: {politician_data.get('name', 'unknown')}")

        # This could trigger reprocessing of related records
        # For now, just log the update

    async def _handle_market_data(self, event_data: Dict[str, Any]):
        """Handle market data updates"""
        market_data = event_data.get("market", {})
        logger.info(f"Received market data update")

        # This could be used to enrich existing records
        # For now, just log the update

    async def _periodic_processing(self):
        """Periodic processing of accumulated data"""
        while self._is_running:
            try:
                # Wait for timeout period
                await asyncio.sleep(self.config.batch_timeout)

                # Process if we have data
                if self.raw_data_buffer:
                    await self._process_accumulated_data()

                # Check if we need to retrain models
                if self._should_trigger_retraining():
                    await self._trigger_model_retraining()

            except Exception as e:
                logger.error(f"Error in periodic processing: {e}")

    async def _process_accumulated_data(self):
        """Process accumulated raw data through ML preprocessing"""
        if not self.raw_data_buffer:
            return

        logger.info(f"Processing {len(self.raw_data_buffer)} accumulated records")

        try:
            # Take snapshot of buffer and clear it
            records_to_process = self.raw_data_buffer.copy()
            self.raw_data_buffer.clear()

            # Run preprocessing
            preprocessing_results = await self._run_preprocessing(records_to_process)

            if preprocessing_results:
                # Save processed data
                await self._save_processed_data(preprocessing_results)

                # Log to MLOps
                if self.config.enable_mlflow_logging:
                    await self._log_preprocessing_metrics(preprocessing_results)

                # Update state
                self._total_records_processed += len(records_to_process)
                self._last_preprocessing_time = datetime.now()

                logger.info(f"Successfully processed {len(records_to_process)} records")

        except Exception as e:
            logger.error(f"Error processing accumulated data: {e}")
            # Re-add records to buffer for retry
            self.raw_data_buffer.extend(records_to_process)

    async def _run_preprocessing(
        self, records: List[Dict[str, Any]]
    ) -> Optional[PreprocessingResults]:
        """Run the preprocessing pipeline"""
        if not records:
            return None

        try:
            # Convert to DataFrame
            raw_df = pd.DataFrame(records)

            # Add metadata
            raw_df["pipeline_batch_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_df["pipeline_version"] = "1.0.0"

            # Run preprocessing
            results = self.preprocessor.preprocess(raw_df)

            return results

        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return None

    async def _save_processed_data(self, results: PreprocessingResults):
        """Save processed data to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save train/val/test splits
        train_path = self.config.model_training_data_dir / f"train_{timestamp}.parquet"
        val_path = self.config.model_training_data_dir / f"val_{timestamp}.parquet"
        test_path = self.config.model_training_data_dir / f"test_{timestamp}.parquet"

        results.train_data.to_parquet(train_path)
        results.val_data.to_parquet(val_path)
        results.test_data.to_parquet(test_path)

        # Save processed data for inference
        processed_path = self.config.processed_data_dir / f"processed_{timestamp}.parquet"
        all_data = pd.concat([results.train_data, results.val_data, results.test_data])
        all_data.to_parquet(processed_path)

        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "feature_names": results.feature_names,
            "categorical_features": results.categorical_features,
            "numerical_features": results.numerical_features,
            "target_columns": results.target_columns,
            "original_shape": results.original_shape,
            "final_shape": results.final_shape,
            "feature_count": results.feature_count,
            "cleaning_stats": asdict(results.cleaning_stats),
        }

        metadata_path = self.config.processed_data_dir / f"metadata_{timestamp}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Saved processed data to {processed_path}")

    async def _log_preprocessing_metrics(self, results: PreprocessingResults):
        """Log preprocessing metrics to MLOps"""
        try:
            # Log parameters
            params = {
                "batch_size": self.config.batch_size,
                "preprocessing_version": "1.0.0",
                "original_records": results.original_shape[0],
                "final_records": results.final_shape[0],
                "feature_count": results.feature_count,
                "target_count": len(results.target_columns),
            }
            self.mlops_manager.log_parameters(params)

            # Log metrics
            metrics = {
                "data_retention_rate": results.final_shape[0] / results.original_shape[0],
                "feature_extraction_ratio": results.feature_count / results.original_shape[1],
                "cleaning_success_rate": results.cleaning_stats.cleaned_records
                / results.cleaning_stats.total_records,
                "outliers_detected": results.cleaning_stats.outliers_detected,
                "missing_values_filled": results.cleaning_stats.missing_values_filled,
            }
            self.mlops_manager.log_metrics(metrics)

            # Log artifacts
            if results.feature_metadata_path and results.feature_metadata_path.exists():
                self.mlops_manager.log_artifacts(results.feature_metadata_path)

        except Exception as e:
            logger.error(f"Failed to log preprocessing metrics: {e}")

    def _should_trigger_retraining(self) -> bool:
        """Check if we should trigger model retraining"""
        if self._total_records_processed >= self.config.auto_retrain_threshold:
            # Reset counter
            self._total_records_processed = 0
            return True
        return False

    async def _trigger_model_retraining(self):
        """Trigger model retraining"""
        logger.info("Triggering model retraining due to data threshold")

        # This would integrate with the model training pipeline
        # For now, just emit an event
        self.lsh_client.emit(
            "ml.retrain.triggered",
            {
                "trigger_reason": "data_threshold",
                "timestamp": datetime.now().isoformat(),
                "records_processed": self._total_records_processed,
            },
        )

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get pipeline processing statistics"""
        return {
            "is_running": self._is_running,
            "raw_buffer_size": len(self.raw_data_buffer),
            "processed_buffer_size": len(self.processed_data_buffer),
            "total_records_processed": self._total_records_processed,
            "last_preprocessing_time": (
                self._last_preprocessing_time.isoformat() if self._last_preprocessing_time else None
            ),
            "config": {
                "batch_size": self.config.batch_size,
                "batch_timeout": self.config.batch_timeout,
                "auto_retrain_threshold": self.config.auto_retrain_threshold,
            },
        }

    async def force_preprocessing(self) -> bool:
        """Force preprocessing of current buffer"""
        if not self.raw_data_buffer:
            logger.warning("No data in buffer to process")
            return False

        await self._process_accumulated_data()
        return True

    async def load_historical_data(self, data_path: Path) -> bool:
        """Load and process historical data"""
        try:
            if data_path.suffix == ".parquet":
                df = pd.read_parquet(data_path)
            elif data_path.suffix == ".csv":
                df = pd.read_csv(data_path)
            elif data_path.suffix == ".json":
                df = pd.read_json(data_path)
            else:
                logger.error(f"Unsupported file format: {data_path.suffix}")
                return False

            # Convert to records and process
            records = df.to_dict("records")
            self.raw_data_buffer.extend(records)

            # Process immediately
            await self._process_accumulated_data()

            logger.info(f"Loaded and processed {len(records)} historical records from {data_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            return False
