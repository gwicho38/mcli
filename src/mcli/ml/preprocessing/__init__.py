"""ML Data Preprocessing Module."""

from .data_cleaners import MissingValueHandler, OutlierDetector, TradingDataCleaner
from .feature_extractors import (
    MarketFeatureExtractor,
    PoliticianFeatureExtractor,
    SentimentFeatureExtractor,
    TemporalFeatureExtractor,
)

# MLDataPipeline and PoliticianTradingPreprocessor were migrated to
# https://github.com/gwicho38/politician-trading-tracker
# These imports are optional to avoid breaking existing code
try:
    from .ml_pipeline import MLDataPipeline, MLDataPipelineConfig

    _ml_pipeline_available = True
except ImportError:
    MLDataPipeline = None  # type: ignore
    MLDataPipelineConfig = None  # type: ignore
    _ml_pipeline_available = False

__all__ = [
    "PoliticianFeatureExtractor",
    "MarketFeatureExtractor",
    "TemporalFeatureExtractor",
    "SentimentFeatureExtractor",
    "TradingDataCleaner",
    "OutlierDetector",
    "MissingValueHandler",
    "MLDataPipeline",
    "MLDataPipelineConfig",
]
