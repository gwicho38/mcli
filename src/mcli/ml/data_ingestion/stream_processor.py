"""Real-time stream processing for financial data"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
import websockets
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Stream processing configuration"""

    buffer_size: int = 1000
    batch_size: int = 100
    flush_interval: int = 5  # seconds
    max_latency: int = 10  # seconds
    enable_deduplication: bool = True
    enable_validation: bool = True
    enable_transformation: bool = True


class DataStream(ABC):
    """Base class for data streams"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.buffer = deque(maxlen=config.buffer_size)
        self.handlers = []
        self.is_running = False
        self.last_flush = time.time()

    @abstractmethod
    async def connect(self):
        """Connect to data source"""
        pass

    @abstractmethod
    async def consume(self) -> AsyncIterator[Dict[str, Any]]:
        """Consume data from stream"""
        pass

    def add_handler(self, handler: Callable):
        """Add data handler"""
        self.handlers.append(handler)

    async def process_message(self, message: Dict[str, Any]):
        """Process single message"""
        # Add to buffer
        self.buffer.append(message)

        # Check if batch processing needed
        if len(self.buffer) >= self.config.batch_size:
            await self.flush_buffer()

        # Check if time-based flush needed
        if time.time() - self.last_flush > self.config.flush_interval:
            await self.flush_buffer()

    async def flush_buffer(self):
        """Flush buffer and process batch"""
        if not self.buffer:
            return

        batch = list(self.buffer)
        self.buffer.clear()
        self.last_flush = time.time()

        # Process batch through handlers
        for handler in self.handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(batch)
                else:
                    handler(batch)
            except Exception as e:
                logger.error(f"Handler error: {e}")

    async def start(self):
        """Start consuming stream"""
        self.is_running = True
        await self.connect()

        try:
            async for message in self.consume():
                if not self.is_running:
                    break
                await self.process_message(message)
        finally:
            await self.flush_buffer()

    async def stop(self):
        """Stop consuming stream"""
        self.is_running = False
        await self.flush_buffer()


class KafkaStream(DataStream):
    """Kafka stream consumer"""

    def __init__(
        self,
        config: StreamConfig,
        bootstrap_servers: str,
        topic: str,
        group_id: str = "ml-processor",
    ):
        super().__init__(config)
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer = None

    async def connect(self):
        """Connect to Kafka"""
        self.consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        logger.info(f"Connected to Kafka topic: {self.topic}")

    async def consume(self) -> AsyncIterator[Dict[str, Any]]:
        """Consume from Kafka"""
        loop = asyncio.get_event_loop()

        while self.is_running:
            # Poll messages
            messages = await loop.run_in_executor(None, self.consumer.poll, 1000)  # timeout ms

            for topic_partition, records in messages.items():
                for record in records:
                    yield record.value


class WebSocketStream(DataStream):
    """WebSocket stream consumer"""

    def __init__(self, config: StreamConfig, url: str):
        super().__init__(config)
        self.url = url
        self.websocket = None

    async def connect(self):
        """Connect to WebSocket"""
        self.websocket = await websockets.connect(self.url)
        logger.info(f"Connected to WebSocket: {self.url}")

    async def consume(self) -> AsyncIterator[Dict[str, Any]]:
        """Consume from WebSocket"""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                yield data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse WebSocket message: {e}")


class StreamProcessor:
    """Process real-time data streams"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.streams = {}
        self.processors = []
        self.metrics = StreamMetrics()

    def add_stream(self, name: str, stream: DataStream):
        """Add data stream"""
        self.streams[name] = stream

        # Add metrics handler
        stream.add_handler(self.update_metrics)

        # Add processors
        for processor in self.processors:
            stream.add_handler(processor)

    def add_processor(self, processor: Callable):
        """Add data processor"""
        self.processors.append(processor)

        # Add to existing streams
        for stream in self.streams.values():
            stream.add_handler(processor)

    async def update_metrics(self, batch: List[Dict[str, Any]]):
        """Update stream metrics"""
        self.metrics.messages_processed += len(batch)
        self.metrics.last_update = datetime.now()

        # Calculate throughput
        current_time = time.time()
        if self.metrics.start_time is None:
            self.metrics.start_time = current_time

        elapsed = current_time - self.metrics.start_time
        if elapsed > 0:
            self.metrics.throughput = self.metrics.messages_processed / elapsed

    async def start(self):
        """Start all streams"""
        tasks = []
        for name, stream in self.streams.items():
            logger.info(f"Starting stream: {name}")
            task = asyncio.create_task(stream.start())
            tasks.append(task)

        await asyncio.gather(*tasks)

    async def stop(self):
        """Stop all streams"""
        for name, stream in self.streams.items():
            logger.info(f"Stopping stream: {name}")
            await stream.stop()

    def get_metrics(self) -> Dict[str, Any]:
        """Get stream metrics"""
        return {
            "messages_processed": self.metrics.messages_processed,
            "throughput": self.metrics.throughput,
            "last_update": (
                self.metrics.last_update.isoformat() if self.metrics.last_update else None
            ),
            "active_streams": len(self.streams),
            "errors": self.metrics.errors,
        }


@dataclass
class StreamMetrics:
    """Stream processing metrics"""

    messages_processed: int = 0
    throughput: float = 0  # messages per second
    last_update: Optional[datetime] = None
    start_time: Optional[float] = None
    errors: int = 0


class DataAggregator:
    """Aggregate data from multiple streams"""

    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.data_buffer = {}
        self.aggregated_data = {}
        self.last_aggregation = time.time()

    async def process_batch(self, batch: List[Dict[str, Any]]):
        """Process batch of messages"""
        for message in batch:
            # Extract key fields
            symbol = message.get("symbol") or message.get("ticker")
            timestamp = message.get("timestamp", time.time())

            if symbol:
                if symbol not in self.data_buffer:
                    self.data_buffer[symbol] = []

                self.data_buffer[symbol].append({"timestamp": timestamp, "data": message})

        # Aggregate if window expired
        if time.time() - self.last_aggregation > self.window_size:
            await self.aggregate()

    async def aggregate(self):
        """Aggregate buffered data"""
        self.last_aggregation = time.time()

        for symbol, data_points in self.data_buffer.items():
            if not data_points:
                continue

            # Sort by timestamp
            data_points.sort(key=lambda x: x["timestamp"])

            # Extract prices
            prices = []
            volumes = []
            for point in data_points:
                data = point["data"]
                if "price" in data:
                    prices.append(data["price"])
                if "volume" in data:
                    volumes.append(data["volume"])

            # Calculate aggregates
            self.aggregated_data[symbol] = {
                "timestamp": self.last_aggregation,
                "count": len(data_points),
                "price_mean": np.mean(prices) if prices else None,
                "price_std": np.std(prices) if prices else None,
                "price_min": min(prices) if prices else None,
                "price_max": max(prices) if prices else None,
                "volume_sum": sum(volumes) if volumes else None,
                "latest": data_points[-1]["data"],
            }

        # Clear buffer
        self.data_buffer.clear()

        logger.info(f"Aggregated data for {len(self.aggregated_data)} symbols")

    def get_aggregated_data(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get aggregated data"""
        if symbol:
            return self.aggregated_data.get(symbol, {})
        return self.aggregated_data


class StreamEnricher:
    """Enrich streaming data with additional context"""

    def __init__(self):
        self.enrichment_cache = {}
        self.cache_ttl = 300  # 5 minutes

    async def enrich_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich batch of messages"""
        enriched = []

        for message in batch:
            enriched_message = await self.enrich_message(message)
            enriched.append(enriched_message)

        return enriched

    async def enrich_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich single message"""
        enriched = message.copy()

        # Add processing metadata
        enriched["processed_at"] = datetime.now().isoformat()
        enriched["processor_version"] = "1.0.0"

        # Enrich based on message type
        if "politician" in message:
            enriched = await self.enrich_political_data(enriched)

        if "ticker" in message or "symbol" in message:
            enriched = await self.enrich_market_data(enriched)

        return enriched

    async def enrich_political_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich political trading data"""
        politician = message.get("politician")

        if politician:
            # Check cache
            cache_key = f"politician_{politician}"
            if cache_key in self.enrichment_cache:
                cached = self.enrichment_cache[cache_key]
                if time.time() - cached["timestamp"] < self.cache_ttl:
                    message["politician_info"] = cached["data"]
                    return message

            # Simulate enrichment (in production, would fetch from database)
            politician_info = {
                "party": "Independent",
                "state": "CA",
                "committees": ["Finance", "Technology"],
                "trading_frequency": "high",
                "avg_trade_size": 50000,
            }

            # Cache enrichment
            self.enrichment_cache[cache_key] = {"timestamp": time.time(), "data": politician_info}

            message["politician_info"] = politician_info

        return message

    async def enrich_market_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich market data"""
        symbol = message.get("ticker") or message.get("symbol")

        if symbol:
            # Check cache
            cache_key = f"market_{symbol}"
            if cache_key in self.enrichment_cache:
                cached = self.enrichment_cache[cache_key]
                if time.time() - cached["timestamp"] < self.cache_ttl:
                    message["market_info"] = cached["data"]
                    return message

            # Simulate enrichment
            market_info = {
                "sector": "Technology",
                "market_cap": "Large",
                "beta": 1.2,
                "pe_ratio": 25.5,
                "dividend_yield": 0.015,
            }

            # Cache enrichment
            self.enrichment_cache[cache_key] = {"timestamp": time.time(), "data": market_info}

            message["market_info"] = market_info

        return message


class KafkaConsumer:
    """Kafka consumer for real-time data"""

    def __init__(self, bootstrap_servers: str, topics: List[str]):
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.consumer = None

    async def connect(self):
        """Connect to Kafka"""
        self.consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            auto_offset_reset="latest",
        )

    async def consume(self, handler: Callable):
        """Consume messages"""
        for message in self.consumer:
            try:
                await handler(message.value)
            except Exception as e:
                logger.error(f"Error processing message: {e}")


class WebSocketConsumer:
    """WebSocket consumer for real-time data"""

    def __init__(self, url: str):
        self.url = url
        self.websocket = None

    async def connect(self):
        """Connect to WebSocket"""
        self.websocket = await websockets.connect(self.url)

    async def consume(self, handler: Callable):
        """Consume messages"""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                await handler(data)
            except Exception as e:
                logger.error(f"Error processing message: {e}")


# Example usage
if __name__ == "__main__":

    async def main():
        # Configure stream processor
        config = StreamConfig(buffer_size=1000, batch_size=100, flush_interval=5)

        processor = StreamProcessor(config)

        # Add WebSocket stream for real-time quotes
        ws_stream = WebSocketStream(config, "wss://stream.example.com/quotes")
        processor.add_stream("quotes", ws_stream)

        # Add Kafka stream for trades
        kafka_stream = KafkaStream(
            config,
            bootstrap_servers="localhost:9092",
            topic="politician-trades",
            group_id="ml-processor",
        )
        processor.add_stream("trades", kafka_stream)

        # Add data aggregator
        aggregator = DataAggregator(window_size=60)
        processor.add_processor(aggregator.process_batch)

        # Add enricher
        enricher = StreamEnricher()
        processor.add_processor(enricher.enrich_batch)

        # Start processing
        try:
            await processor.start()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await processor.stop()

    asyncio.run(main())
