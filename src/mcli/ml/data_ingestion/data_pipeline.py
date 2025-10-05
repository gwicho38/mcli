"""Complete data ingestion pipeline with validation and transformation"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from .api_connectors import (
    AlphaVantageConnector,
    CongressionalDataAPI,
    DataAggregator,
    PolygonIOConnector,
    QuiverQuantConnector,
    YahooFinanceConnector,
)
from .stream_processor import DataAggregator as StreamAggregator
from .stream_processor import StreamConfig, StreamProcessor

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Data pipeline configuration"""

    data_dir: Path = Path("data")
    batch_size: int = 1000
    enable_streaming: bool = True
    enable_validation: bool = True
    enable_transformation: bool = True
    enable_caching: bool = True
    cache_ttl: int = 300  # seconds
    retry_count: int = 3
    retry_delay: int = 1


class DataValidator:
    """Validate incoming data"""

    def __init__(self):
        self.validation_rules = {
            "politician_trades": self._validate_politician_trade,
            "stock_quotes": self._validate_stock_quote,
            "market_data": self._validate_market_data,
        }
        self.validation_stats = {"total": 0, "valid": 0, "invalid": 0, "errors": []}

    def validate(self, data: Dict[str, Any], data_type: str) -> bool:
        """Validate data based on type"""
        self.validation_stats["total"] += 1

        if data_type not in self.validation_rules:
            logger.warning(f"Unknown data type: {data_type}")
            return True

        try:
            is_valid = self.validation_rules[data_type](data)
            if is_valid:
                self.validation_stats["valid"] += 1
            else:
                self.validation_stats["invalid"] += 1
            return is_valid
        except Exception as e:
            self.validation_stats["invalid"] += 1
            self.validation_stats["errors"].append(str(e))
            logger.error(f"Validation error: {e}")
            return False

    def _validate_politician_trade(self, data: Dict[str, Any]) -> bool:
        """Validate politician trading data"""
        required_fields = ["politician", "ticker", "transaction_type", "amount", "transaction_date"]

        # Check required fields
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False

        # Validate transaction type
        if data["transaction_type"] not in ["buy", "sell", "exchange"]:
            logger.warning(f"Invalid transaction type: {data['transaction_type']}")
            return False

        # Validate amount
        if not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
            logger.warning(f"Invalid amount: {data['amount']}")
            return False

        # Validate date
        try:
            if isinstance(data["transaction_date"], str):
                datetime.fromisoformat(data["transaction_date"])
        except:
            logger.warning(f"Invalid date format: {data['transaction_date']}")
            return False

        return True

    def _validate_stock_quote(self, data: Dict[str, Any]) -> bool:
        """Validate stock quote data"""
        required_fields = ["symbol", "price", "timestamp"]

        for field in required_fields:
            if field not in data:
                return False

        # Validate price
        if not isinstance(data["price"], (int, float)) or data["price"] <= 0:
            return False

        return True

    def _validate_market_data(self, data: Dict[str, Any]) -> bool:
        """Validate market data"""
        required_fields = ["symbol", "close", "volume", "date"]

        for field in required_fields:
            if field not in data:
                return False

        # Validate prices
        for price_field in ["close", "open", "high", "low"]:
            if price_field in data:
                if not isinstance(data[price_field], (int, float)) or data[price_field] <= 0:
                    return False

        # Validate volume
        if not isinstance(data["volume"], (int, float)) or data["volume"] < 0:
            return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return self.validation_stats.copy()


class DataTransformer:
    """Transform and normalize data"""

    def __init__(self):
        self.transformers = {
            "politician_trades": self._transform_politician_trade,
            "stock_quotes": self._transform_stock_quote,
            "market_data": self._transform_market_data,
        }

    def transform(
        self, data: Union[Dict[str, Any], List[Dict[str, Any]]], data_type: str
    ) -> Union[Dict[str, Any], pd.DataFrame]:
        """Transform data based on type"""
        if data_type not in self.transformers:
            return data

        if isinstance(data, list):
            transformed = [self.transformers[data_type](item) for item in data]
            return pd.DataFrame(transformed)
        else:
            return self.transformers[data_type](data)

    def _transform_politician_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform politician trading data"""
        transformed = data.copy()

        # Standardize politician name
        transformed["politician_normalized"] = self._normalize_name(data.get("politician", ""))

        # Convert dates to datetime
        if "transaction_date" in data:
            transformed["transaction_date"] = pd.to_datetime(data["transaction_date"])

        if "disclosure_date" in data:
            transformed["disclosure_date"] = pd.to_datetime(data["disclosure_date"])

            # Calculate disclosure delay
            if "transaction_date" in transformed:
                delay = (transformed["disclosure_date"] - transformed["transaction_date"]).days
                transformed["disclosure_delay_days"] = max(0, delay)

        # Normalize ticker
        transformed["ticker"] = data.get("ticker", "").upper()

        # Categorize transaction amount
        amount = data.get("amount", 0)
        transformed["amount_category"] = self._categorize_amount(amount)

        # Add derived features
        transformed["is_purchase"] = data.get("transaction_type") == "buy"
        transformed["is_sale"] = data.get("transaction_type") == "sell"

        return transformed

    def _transform_stock_quote(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform stock quote data"""
        transformed = data.copy()

        # Normalize symbol
        transformed["symbol"] = data.get("symbol", "").upper()

        # Convert timestamp
        if "timestamp" in data:
            if isinstance(data["timestamp"], (int, float)):
                transformed["timestamp"] = datetime.fromtimestamp(data["timestamp"])
            else:
                transformed["timestamp"] = pd.to_datetime(data["timestamp"])

        # Calculate spread if bid/ask available
        if "bid" in data and "ask" in data:
            transformed["spread"] = data["ask"] - data["bid"]
            transformed["spread_pct"] = (transformed["spread"] / data["ask"]) * 100

        return transformed

    def _transform_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform market data"""
        transformed = data.copy()

        # Normalize symbol
        transformed["symbol"] = data.get("symbol", "").upper()

        # Convert date
        if "date" in data:
            transformed["date"] = pd.to_datetime(data["date"])

        # Calculate OHLC metrics
        if all(k in data for k in ["open", "high", "low", "close"]):
            transformed["daily_range"] = data["high"] - data["low"]
            transformed["daily_return"] = (data["close"] - data["open"]) / data["open"]
            transformed["intraday_volatility"] = transformed["daily_range"] / data["close"]

        # Calculate volume metrics
        if "volume" in data and "close" in data:
            transformed["dollar_volume"] = data["volume"] * data["close"]

        return transformed

    def _normalize_name(self, name: str) -> str:
        """Normalize politician name"""
        # Remove titles
        titles = ["Sen.", "Senator", "Rep.", "Representative", "Hon.", "Dr.", "Mr.", "Mrs.", "Ms."]
        normalized = name
        for title in titles:
            normalized = normalized.replace(title, "")

        # Clean and standardize
        normalized = " ".join(normalized.split())  # Remove extra spaces
        normalized = normalized.strip()

        return normalized

    def _categorize_amount(self, amount: float) -> str:
        """Categorize transaction amount"""
        if amount < 1000:
            return "micro"
        elif amount < 15000:
            return "small"
        elif amount < 50000:
            return "medium"
        elif amount < 250000:
            return "large"
        elif amount < 1000000:
            return "very_large"
        else:
            return "mega"


class DataLoader:
    """Load data to storage"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def save_batch(
        self, data: pd.DataFrame, data_type: str, timestamp: Optional[datetime] = None
    ):
        """Save batch of data"""
        if timestamp is None:
            timestamp = datetime.now()

        # Create subdirectory for data type
        type_dir = self.data_dir / data_type
        type_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        filename = f"{data_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.parquet"
        filepath = type_dir / filename

        # Save as parquet
        data.to_parquet(filepath, compression="snappy")
        logger.info(f"Saved {len(data)} records to {filepath}")

        return filepath

    async def save_json(
        self, data: Union[Dict, List], data_type: str, timestamp: Optional[datetime] = None
    ):
        """Save data as JSON"""
        if timestamp is None:
            timestamp = datetime.now()

        # Create subdirectory
        type_dir = self.data_dir / data_type
        type_dir.mkdir(exist_ok=True)

        # Generate filename
        filename = f"{data_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = type_dir / filename

        # Save JSON
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved JSON to {filepath}")
        return filepath

    def load_latest(self, data_type: str, n_files: int = 1) -> pd.DataFrame:
        """Load latest data files"""
        type_dir = self.data_dir / data_type

        if not type_dir.exists():
            return pd.DataFrame()

        # Find parquet files
        files = sorted(type_dir.glob("*.parquet"), key=lambda x: x.stat().st_mtime, reverse=True)

        if not files:
            return pd.DataFrame()

        # Load and concatenate
        dfs = []
        for file in files[:n_files]:
            df = pd.read_parquet(file)
            dfs.append(df)

        return pd.concat(dfs, ignore_index=True)


class IngestionPipeline:
    """Complete data ingestion pipeline"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.validator = DataValidator()
        self.transformer = DataTransformer()
        self.loader = DataLoader(config.data_dir)

        # Initialize data sources
        self.sources = {}
        self.stream_processor = None

        # Pipeline metrics
        self.metrics = {
            "records_processed": 0,
            "records_validated": 0,
            "records_transformed": 0,
            "records_saved": 0,
            "errors": 0,
            "start_time": None,
            "last_update": None,
        }

    def add_source(self, name: str, connector):
        """Add data source"""
        self.sources[name] = connector
        logger.info(f"Added data source: {name}")

    async def initialize_sources(self):
        """Initialize all data sources"""
        # Congressional data
        congress_api = CongressionalDataAPI()
        self.add_source("congress", congress_api)

        # Stock data sources
        yahoo = YahooFinanceConnector()
        self.add_source("yahoo", yahoo)

        # Add more sources as needed
        logger.info(f"Initialized {len(self.sources)} data sources")

    async def process_batch(self, data: List[Dict[str, Any]], data_type: str) -> pd.DataFrame:
        """Process batch of data through pipeline"""
        processed_data = []

        for record in data:
            # Validate
            if self.config.enable_validation:
                if not self.validator.validate(record, data_type):
                    self.metrics["errors"] += 1
                    continue
                self.metrics["records_validated"] += 1

            # Transform
            if self.config.enable_transformation:
                record = self.transformer.transform(record, data_type)
                self.metrics["records_transformed"] += 1

            processed_data.append(record)
            self.metrics["records_processed"] += 1

        # Convert to DataFrame
        if processed_data:
            df = pd.DataFrame(processed_data)

            # Save to storage
            await self.loader.save_batch(df, data_type)
            self.metrics["records_saved"] += len(df)

            return df

        return pd.DataFrame()

    async def fetch_politician_trades(self, days: int = 30) -> pd.DataFrame:
        """Fetch recent politician trades"""
        congress_api = self.sources.get("congress")
        if not congress_api:
            logger.error("Congressional data source not available")
            return pd.DataFrame()

        # Fetch trades
        trades = await congress_api.fetch_recent_trades(days=days)

        # Process through pipeline
        df = await self.process_batch(trades, "politician_trades")

        logger.info(f"Fetched {len(df)} politician trades")
        return df

    async def fetch_stock_data(
        self, tickers: List[str], period: str = "1mo"
    ) -> Dict[str, pd.DataFrame]:
        """Fetch stock data for multiple tickers"""
        stock_data = {}

        for ticker in tickers:
            # Try Yahoo Finance first
            yahoo = self.sources.get("yahoo")
            if yahoo:
                try:
                    df = await yahoo.fetch_historical(ticker, period)
                    if not df.empty:
                        # Process through pipeline
                        records = df.to_dict("records")
                        for record in records:
                            record["symbol"] = ticker

                        processed = await self.process_batch(records, "market_data")
                        stock_data[ticker] = processed
                except Exception as e:
                    logger.error(f"Failed to fetch {ticker}: {e}")

        return stock_data

    async def start_streaming(self):
        """Start real-time streaming"""
        if not self.config.enable_streaming:
            logger.info("Streaming disabled")
            return

        # Initialize stream processor
        stream_config = StreamConfig(
            buffer_size=self.config.batch_size, batch_size=100, flush_interval=5
        )

        self.stream_processor = StreamProcessor(stream_config)

        # Add processor for pipeline
        async def pipeline_processor(batch):
            await self.process_batch(batch, "streaming_data")

        self.stream_processor.add_processor(pipeline_processor)

        # Start streaming
        await self.stream_processor.start()

    async def stop_streaming(self):
        """Stop streaming"""
        if self.stream_processor:
            await self.stream_processor.stop()

    async def run(self, mode: str = "batch"):
        """Run ingestion pipeline"""
        self.metrics["start_time"] = datetime.now()

        try:
            # Initialize sources
            await self.initialize_sources()

            if mode == "batch":
                # Batch processing
                await self.run_batch()
            elif mode == "streaming":
                # Streaming mode
                await self.start_streaming()
            elif mode == "hybrid":
                # Both batch and streaming
                batch_task = asyncio.create_task(self.run_batch())
                stream_task = asyncio.create_task(self.start_streaming())
                await asyncio.gather(batch_task, stream_task)

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.metrics["errors"] += 1
            raise
        finally:
            self.metrics["last_update"] = datetime.now()

    async def run_batch(self):
        """Run batch processing"""
        logger.info("Starting batch processing...")

        # Fetch politician trades
        trades_df = await self.fetch_politician_trades(days=30)

        # Extract unique tickers
        if not trades_df.empty and "ticker" in trades_df.columns:
            tickers = trades_df["ticker"].unique().tolist()

            # Fetch stock data for those tickers
            stock_data = await self.fetch_stock_data(tickers[:20])  # Limit to 20 for demo

            logger.info(f"Processed {len(trades_df)} trades and {len(stock_data)} stocks")

    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline metrics"""
        metrics = self.metrics.copy()

        # Calculate throughput
        if metrics["start_time"]:
            elapsed = (datetime.now() - metrics["start_time"]).total_seconds()
            if elapsed > 0:
                metrics["throughput"] = metrics["records_processed"] / elapsed

        # Add validation stats
        metrics["validation_stats"] = self.validator.get_stats()

        return metrics


# Example usage
if __name__ == "__main__":

    async def main():
        # Configure pipeline
        config = PipelineConfig(
            data_dir=Path("data/ingestion"),
            enable_streaming=False,  # Batch mode for testing
            enable_validation=True,
            enable_transformation=True,
        )

        # Create pipeline
        pipeline = IngestionPipeline(config)

        # Run batch processing
        await pipeline.run(mode="batch")

        # Get metrics
        metrics = pipeline.get_metrics()
        print(f"Pipeline metrics: {json.dumps(metrics, indent=2, default=str)}")

    asyncio.run(main())
