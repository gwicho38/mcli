"""REST API for model serving"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import torch
import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from ml.features.ensemble_features import EnsembleFeatureBuilder
from ml.features.political_features import PoliticalInfluenceFeatures
from ml.features.stock_features import StockRecommendationFeatures
from ml.models.recommendation_models import PortfolioRecommendation, StockRecommendationModel

logger = logging.getLogger(__name__)


# Pydantic models for API
class PredictionRequest(BaseModel):
    """Request model for predictions"""

    trading_data: Dict[str, Any] = Field(..., description="Politician trading data")
    stock_data: Optional[Dict[str, Any]] = Field(None, description="Stock price data")
    tickers: List[str] = Field(..., description="Stock tickers to analyze")
    features: Optional[Dict[str, float]] = Field(None, description="Pre-computed features")


class PredictionResponse(BaseModel):
    """Response model for predictions"""

    recommendations: List[Dict[str, Any]]
    timestamp: str
    model_version: str
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    model_loaded: bool
    model_version: Optional[str]
    uptime_seconds: float


class ModelMetricsResponse(BaseModel):
    """Model metrics response"""

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    last_updated: str


class BatchPredictionRequest(BaseModel):
    """Batch prediction request"""

    batch_id: str
    data: List[PredictionRequest]


class BatchPredictionResponse(BaseModel):
    """Batch prediction response"""

    batch_id: str
    status: str
    progress: float
    results: Optional[List[PredictionResponse]]


class ModelEndpoint:
    """Model endpoint manager"""

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path
        self.model_version = "1.0.0"
        self.feature_extractors = {}
        self.start_time = datetime.now()
        self.prediction_cache = {}
        self.metrics = {"total_predictions": 0, "avg_latency_ms": 0, "cache_hits": 0, "errors": 0}

        if model_path:
            self.load_model(model_path)

        self._setup_feature_extractors()

    def _setup_feature_extractors(self):
        """Initialize feature extractors"""
        self.feature_extractors = {
            "stock": StockRecommendationFeatures(),
            "political": PoliticalInfluenceFeatures(),
            "ensemble": EnsembleFeatureBuilder(),
        }
        logger.info("Feature extractors initialized")

    def load_model(self, model_path: str):
        """Load model from file"""
        try:
            checkpoint = torch.load(model_path, map_location="cpu")

            # Reconstruct model (simplified - would need proper config)
            from ml.models.ensemble_models import EnsembleConfig, ModelConfig
            from ml.models.recommendation_models import RecommendationConfig

            # Create dummy config for loading
            model_configs = [
                ModelConfig(
                    model_type="mlp",
                    hidden_dims=[256, 128],
                    dropout_rate=0.3,
                    learning_rate=0.001,
                    weight_decay=1e-4,
                    batch_size=32,
                    epochs=10,
                )
            ]

            ensemble_config = EnsembleConfig(base_models=model_configs)
            recommendation_config = RecommendationConfig(ensemble_config=ensemble_config)

            # Initialize model (need to know input dimension)
            input_dim = 100  # Default, would be stored in checkpoint
            self.model = StockRecommendationModel(input_dim, recommendation_config)

            # Load state
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.model.eval()

            self.model_version = checkpoint.get("version", "1.0.0")
            logger.info(f"Model loaded from {model_path} (version: {self.model_version})")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def extract_features(
        self, trading_data: pd.DataFrame, stock_data: Optional[pd.DataFrame] = None
    ) -> np.ndarray:
        """Extract features from raw data"""
        features = pd.DataFrame()

        # Extract political features
        if not trading_data.empty:
            political_features = self.feature_extractors["political"].extract_influence_features(
                trading_data
            )
            features = pd.concat([features, political_features], axis=1)

        # Extract stock features if available
        if stock_data is not None and not stock_data.empty:
            try:
                stock_features = self.feature_extractors["stock"].extract_features(stock_data)
                features = pd.concat([features, stock_features], axis=1)
            except Exception as e:
                logger.warning(f"Could not extract stock features: {e}")

        # Build ensemble features
        if not features.empty:
            features = self.feature_extractors["ensemble"].build_ensemble_features(features)

        return features.values if not features.empty else np.array([[]])

    async def predict(self, request: PredictionRequest) -> PredictionResponse:
        """Generate predictions"""
        start_time = datetime.now()

        try:
            # Check cache
            cache_key = json.dumps(request.dict(), sort_keys=True)
            if cache_key in self.prediction_cache:
                self.metrics["cache_hits"] += 1
                cached_response = self.prediction_cache[cache_key]
                cached_response.processing_time_ms = 0.1  # Cache hit is fast
                return cached_response

            # Convert request data to DataFrames
            trading_df = pd.DataFrame([request.trading_data])
            stock_df = pd.DataFrame([request.stock_data]) if request.stock_data else None

            # Extract features or use provided features
            if request.features:
                features = np.array([list(request.features.values())])
            else:
                features = self.extract_features(trading_df, stock_df)

            # Generate recommendations
            if self.model:
                recommendations = self.model.generate_recommendations(
                    features, request.tickers, market_data=stock_df
                )
            else:
                # Mock recommendations if no model loaded
                recommendations = self._generate_mock_recommendations(request.tickers)

            # Convert recommendations to dict
            recommendations_dict = [
                {
                    "ticker": rec.ticker,
                    "score": rec.recommendation_score,
                    "confidence": rec.confidence,
                    "risk_level": rec.risk_level,
                    "expected_return": rec.expected_return,
                    "position_size": rec.position_size,
                    "entry_price": rec.entry_price,
                    "target_price": rec.target_price,
                    "stop_loss": rec.stop_loss,
                    "reason": rec.recommendation_reason,
                }
                for rec in recommendations
            ]

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Update metrics
            self.metrics["total_predictions"] += 1
            self.metrics["avg_latency_ms"] = (
                self.metrics["avg_latency_ms"] * (self.metrics["total_predictions"] - 1)
                + processing_time
            ) / self.metrics["total_predictions"]

            response = PredictionResponse(
                recommendations=recommendations_dict,
                timestamp=datetime.now().isoformat(),
                model_version=self.model_version,
                processing_time_ms=processing_time,
            )

            # Cache response
            self.prediction_cache[cache_key] = response

            # Limit cache size
            if len(self.prediction_cache) > 1000:
                # Remove oldest entries
                keys_to_remove = list(self.prediction_cache.keys())[:100]
                for key in keys_to_remove:
                    del self.prediction_cache[key]

            return response

        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Prediction error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _generate_mock_recommendations(self, tickers: List[str]) -> List[PortfolioRecommendation]:
        """Generate mock recommendations for testing"""
        recommendations = []
        for ticker in tickers:
            rec = PortfolioRecommendation(
                ticker=ticker,
                recommendation_score=np.random.random(),
                confidence=np.random.random(),
                risk_level=np.random.choice(["low", "medium", "high"]),
                expected_return=np.random.normal(0.05, 0.15),
                risk_adjusted_score=np.random.random(),
                position_size=np.random.uniform(0.01, 0.1),
                recommendation_reason="Mock recommendation for testing",
            )
            recommendations.append(rec)
        return recommendations

    def get_health(self) -> HealthResponse:
        """Get endpoint health status"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        return HealthResponse(
            status="healthy",
            model_loaded=self.model is not None,
            model_version=self.model_version,
            uptime_seconds=uptime,
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get endpoint metrics"""
        return {
            **self.metrics,
            "model_version": self.model_version,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "cache_size": len(self.prediction_cache),
        }


class PredictionService:
    """Async prediction service for batch processing"""

    def __init__(self, model_endpoint: ModelEndpoint):
        self.model_endpoint = model_endpoint
        self.batch_jobs = {}
        self.executor = None

    async def process_batch(self, batch_request: BatchPredictionRequest) -> BatchPredictionResponse:
        """Process batch predictions asynchronously"""
        batch_id = batch_request.batch_id

        # Initialize batch job
        self.batch_jobs[batch_id] = {
            "status": "processing",
            "progress": 0.0,
            "results": [],
            "start_time": datetime.now(),
        }

        # Process each request
        results = []
        total = len(batch_request.data)

        for i, request in enumerate(batch_request.data):
            try:
                result = await self.model_endpoint.predict(request)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch prediction error for item {i}: {e}")
                results.append(None)

            # Update progress
            self.batch_jobs[batch_id]["progress"] = (i + 1) / total

        # Update job status
        self.batch_jobs[batch_id]["status"] = "completed"
        self.batch_jobs[batch_id]["results"] = results
        self.batch_jobs[batch_id]["end_time"] = datetime.now()

        return BatchPredictionResponse(
            batch_id=batch_id, status="completed", progress=1.0, results=results
        )

    def get_batch_status(self, batch_id: str) -> BatchPredictionResponse:
        """Get batch job status"""
        if batch_id not in self.batch_jobs:
            raise HTTPException(status_code=404, detail="Batch job not found")

        job = self.batch_jobs[batch_id]

        return BatchPredictionResponse(
            batch_id=batch_id,
            status=job["status"],
            progress=job["progress"],
            results=job.get("results"),
        )


class ModelServer:
    """FastAPI model server"""

    def __init__(self, model_path: Optional[str] = None):
        self.model_endpoint = ModelEndpoint(model_path)
        self.prediction_service = PredictionService(self.model_endpoint)
        self.app = self._create_app()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Manage application lifecycle"""
        # Startup
        logger.info("Starting model server...")
        yield
        # Shutdown
        logger.info("Shutting down model server...")

    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="Stock Recommendation API",
            description="ML-powered stock recommendation system based on politician trading data",
            version="1.0.0",
            lifespan=self.lifespan,
        )

        # Health check
        @app.get("/health", response_model=HealthResponse)
        async def health():
            """Health check endpoint"""
            return self.model_endpoint.get_health()

        # Metrics
        @app.get("/metrics")
        async def metrics():
            """Get service metrics"""
            return self.model_endpoint.get_metrics()

        # Single prediction
        @app.post("/predict", response_model=PredictionResponse)
        async def predict(request: PredictionRequest):
            """Generate stock recommendations"""
            return await self.model_endpoint.predict(request)

        # Batch prediction
        @app.post("/batch/predict", response_model=BatchPredictionResponse)
        async def batch_predict(
            batch_request: BatchPredictionRequest, background_tasks: BackgroundTasks
        ):
            """Submit batch prediction job"""
            background_tasks.add_task(self.prediction_service.process_batch, batch_request)

            return BatchPredictionResponse(
                batch_id=batch_request.batch_id, status="submitted", progress=0.0, results=None
            )

        # Batch status
        @app.get("/batch/{batch_id}", response_model=BatchPredictionResponse)
        async def batch_status(batch_id: str):
            """Get batch job status"""
            return self.prediction_service.get_batch_status(batch_id)

        # Model reload
        @app.post("/model/reload")
        async def reload_model(model_path: str):
            """Reload model from new path"""
            try:
                self.model_endpoint.load_model(model_path)
                return {"status": "success", "model_version": self.model_endpoint.model_version}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # Upload and predict
        @app.post("/upload/predict")
        async def upload_predict(file: UploadFile = File(...)):
            """Upload CSV and get predictions"""
            try:
                # Read uploaded file
                content = await file.read()
                df = pd.read_csv(pd.io.common.BytesIO(content))

                # Extract tickers
                tickers = (
                    df["ticker_cleaned"].unique().tolist() if "ticker_cleaned" in df.columns else []
                )

                # Create request
                request = PredictionRequest(
                    trading_data=df.to_dict(orient="records")[0] if len(df) > 0 else {},
                    tickers=tickers[:5],  # Limit to 5 tickers
                )

                return await self.model_endpoint.predict(request)

            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        return app

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the server"""
        uvicorn.run(self.app, host=host, port=port)


def main():
    """Run the model server"""
    import argparse

    parser = argparse.ArgumentParser(description="Stock Recommendation Model Server")
    parser.add_argument("--model-path", type=str, help="Path to model file")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")

    args = parser.parse_args()

    server = ModelServer(args.model_path)
    server.run(args.host, args.port)


if __name__ == "__main__":
    main()
