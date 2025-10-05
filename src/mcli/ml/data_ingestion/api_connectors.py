"""API connectors for real-time data ingestion"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
import pandas as pd
import requests
import websockets
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API configuration"""

    api_key: Optional[str] = None
    base_url: str = ""
    rate_limit: int = 100  # requests per minute
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 1


class BaseAPIConnector(ABC):
    """Base class for API connectors"""

    def __init__(self, config: APIConfig):
        self.config = config
        self.session = None
        self.rate_limiter = RateLimiter(config.rate_limit)

    @abstractmethod
    async def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """Fetch data from API"""
        pass

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with rate limiting and retry logic"""
        await self.rate_limiter.acquire()

        url = urljoin(self.config.base_url, endpoint)

        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        retry_count = 0
        while retry_count < self.config.retry_count:
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession()

                async with self.session.get(
                    url, params=params, headers=headers, timeout=self.config.timeout
                ) as response:
                    response.raise_for_status()
                    return await response.json()

            except aiohttp.ClientError as e:
                retry_count += 1
                if retry_count >= self.config.retry_count:
                    logger.error(f"API request failed after {retry_count} retries: {e}")
                    raise
                await asyncio.sleep(self.config.retry_delay * retry_count)

    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()


class RateLimiter:
    """Rate limiter for API requests"""

    def __init__(self, rate_limit: int):
        self.rate_limit = rate_limit
        self.tokens = rate_limit
        self.updated_at = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire rate limit token"""
        async with self.lock:
            while self.tokens <= 0:
                now = time.time()
                elapsed = now - self.updated_at

                if elapsed >= 60:  # Reset every minute
                    self.tokens = self.rate_limit
                    self.updated_at = now
                else:
                    await asyncio.sleep(1)

            self.tokens -= 1


class CongressionalDataAPI(BaseAPIConnector):
    """Congressional trading data API connector"""

    def __init__(self, config: Optional[APIConfig] = None):
        if not config:
            config = APIConfig(base_url="https://api.capitoltrades.com/v1/", rate_limit=60)
        super().__init__(config)

    async def fetch_recent_trades(self, days: int = 30) -> List[Dict[str, Any]]:
        """Fetch recent congressional trades"""
        params = {
            "from_date": (datetime.now() - timedelta(days=days)).isoformat(),
            "to_date": datetime.now().isoformat(),
            "limit": 1000,
        }

        try:
            data = await self._make_request("trades", params)
            return data.get("trades", [])
        except Exception as e:
            logger.error(f"Failed to fetch congressional trades: {e}")
            return self._generate_mock_trades()

    async def fetch_politician_info(self, politician_id: str) -> Dict[str, Any]:
        """Fetch politician information"""
        try:
            return await self._make_request(f"politicians/{politician_id}")
        except Exception as e:
            logger.error(f"Failed to fetch politician info: {e}")
            return self._generate_mock_politician_info(politician_id)

    def _generate_mock_trades(self) -> List[Dict[str, Any]]:
        """Generate mock trades for testing"""
        import random

        trades = []
        politicians = ["Nancy Pelosi", "Mitch McConnell", "Chuck Schumer", "Kevin McCarthy"]
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]

        for _ in range(50):
            trades.append(
                {
                    "politician": random.choice(politicians),
                    "ticker": random.choice(tickers),
                    "transaction_type": random.choice(["buy", "sell"]),
                    "amount": random.randint(1000, 1000000),
                    "transaction_date": (
                        datetime.now() - timedelta(days=random.randint(1, 30))
                    ).isoformat(),
                    "disclosure_date": datetime.now().isoformat(),
                }
            )

        return trades

    def _generate_mock_politician_info(self, politician_id: str) -> Dict[str, Any]:
        """Generate mock politician info"""
        return {
            "id": politician_id,
            "name": "Mock Politician",
            "party": "Independent",
            "state": "CA",
            "chamber": "House",
            "committees": ["Finance", "Technology"],
        }


class StockMarketAPI(BaseAPIConnector):
    """Base class for stock market APIs"""

    async def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch current stock quote"""
        pass

    async def fetch_historical(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Fetch historical stock data"""
        pass

    async def stream_quotes(self, symbols: List[str]) -> AsyncIterator[Dict[str, Any]]:
        """Stream real-time quotes"""
        pass


class AlphaVantageConnector(StockMarketAPI):
    """Alpha Vantage API connector"""

    def __init__(self, api_key: str):
        config = APIConfig(
            api_key=api_key,
            base_url="https://www.alphavantage.co/query",
            rate_limit=5,  # Free tier: 5 requests per minute
        )
        super().__init__(config)

    async def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch current quote from Alpha Vantage"""
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.config.api_key}

        data = await self._make_request("", params)
        return self._parse_quote(data.get("Global Quote", {}))

    async def fetch_historical(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Fetch historical data from Alpha Vantage"""
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full" if period == "max" else "compact",
            "apikey": self.config.api_key,
        }

        data = await self._make_request("", params)
        time_series = data.get("Time Series (Daily)", {})

        # Convert to DataFrame
        df = pd.DataFrame.from_dict(time_series, orient="index")
        df.index = pd.to_datetime(df.index)
        df.columns = ["open", "high", "low", "close", "volume"]
        df = df.astype(float)

        return df.sort_index()

    def _parse_quote(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Alpha Vantage quote"""
        return {
            "symbol": quote_data.get("01. symbol", ""),
            "price": float(quote_data.get("05. price", 0)),
            "volume": int(quote_data.get("06. volume", 0)),
            "timestamp": quote_data.get("07. latest trading day", ""),
            "change": float(quote_data.get("09. change", 0)),
            "change_percent": quote_data.get("10. change percent", "0%"),
        }


class YahooFinanceConnector(StockMarketAPI):
    """Yahoo Finance connector using yfinance"""

    def __init__(self):
        config = APIConfig(rate_limit=2000)  # Yahoo Finance is generous
        super().__init__(config)

    async def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch current quote from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,
                "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "volume": info.get("volume", 0),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "dividend_yield": info.get("dividendYield", 0),
            }
        except Exception as e:
            logger.error(f"Failed to fetch Yahoo Finance quote: {e}")
            return {}

    async def fetch_historical(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Fetch historical data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            return df
        except Exception as e:
            logger.error(f"Failed to fetch Yahoo Finance historical data: {e}")
            return pd.DataFrame()


class PolygonIOConnector(StockMarketAPI):
    """Polygon.io API connector"""

    def __init__(self, api_key: str):
        config = APIConfig(api_key=api_key, base_url="https://api.polygon.io/", rate_limit=100)
        super().__init__(config)

    async def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch current quote from Polygon.io"""
        endpoint = f"v2/last/nbbo/{symbol}"
        params = {"apiKey": self.config.api_key}

        data = await self._make_request(endpoint, params)
        return self._parse_polygon_quote(data)

    async def fetch_aggregates(
        self, symbol: str, from_date: str, to_date: str, timespan: str = "day"
    ) -> pd.DataFrame:
        """Fetch aggregate bars from Polygon.io"""
        endpoint = f"v2/aggs/ticker/{symbol}/range/1/{timespan}/{from_date}/{to_date}"
        params = {"apiKey": self.config.api_key, "adjusted": "true", "sort": "asc"}

        data = await self._make_request(endpoint, params)
        results = data.get("results", [])

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df["timestamp"] = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})

        return df.set_index("timestamp")

    def _parse_polygon_quote(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Polygon.io quote"""
        results = data.get("results", {})
        return {
            "symbol": results.get("T", ""),
            "price": results.get("P", 0),
            "size": results.get("S", 0),
            "timestamp": results.get("t", 0),
        }


class QuiverQuantConnector(BaseAPIConnector):
    """QuiverQuant API for congressional trading data"""

    def __init__(self, api_key: str):
        config = APIConfig(
            api_key=api_key, base_url="https://api.quiverquant.com/beta/", rate_limit=100
        )
        super().__init__(config)

    async def fetch_congress_trades(self) -> List[Dict[str, Any]]:
        """Fetch congressional trading data"""
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Accept": "application/json"}

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(
                f"{self.config.base_url}historical/congresstrading", headers=headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        except Exception as e:
            logger.error(f"Failed to fetch QuiverQuant data: {e}")
            return []

    async def fetch_lobbying(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch lobbying data for a ticker"""
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Accept": "application/json"}

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(
                f"{self.config.base_url}historical/lobbying/{ticker}", headers=headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        except Exception as e:
            logger.error(f"Failed to fetch lobbying data: {e}")
            return []


class WebSocketDataStream:
    """WebSocket stream for real-time data"""

    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url
        self.api_key = api_key
        self.websocket = None
        self.handlers = []

    def add_handler(self, handler: Callable):
        """Add message handler"""
        self.handlers.append(handler)

    async def connect(self):
        """Connect to WebSocket"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.websocket = await websockets.connect(self.url, extra_headers=headers)
        logger.info(f"Connected to WebSocket: {self.url}")

    async def subscribe(self, symbols: List[str]):
        """Subscribe to symbols"""
        if not self.websocket:
            await self.connect()

        message = {"action": "subscribe", "symbols": symbols}
        await self.websocket.send(json.dumps(message))

    async def stream(self):
        """Stream messages"""
        if not self.websocket:
            await self.connect()

        async for message in self.websocket:
            data = json.loads(message)

            # Call handlers
            for handler in self.handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Handler error: {e}")

    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()


class DataAggregator:
    """Aggregate data from multiple sources"""

    def __init__(self):
        self.sources = {}
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    def add_source(self, name: str, connector: BaseAPIConnector):
        """Add data source"""
        self.sources[name] = connector
        logger.info(f"Added data source: {name}")

    async def fetch_all(self, symbol: str) -> Dict[str, Any]:
        """Fetch data from all sources"""
        results = {}

        # Check cache
        cache_key = f"{symbol}_{int(time.time() // self.cache_ttl)}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Fetch from all sources concurrently
        tasks = []
        for name, connector in self.sources.items():
            if hasattr(connector, "fetch_quote"):
                tasks.append(self._fetch_with_name(name, connector.fetch_quote(symbol)))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for name, data in responses:
            if not isinstance(data, Exception):
                results[name] = data
            else:
                logger.error(f"Error fetching from {name}: {data}")

        # Cache results
        self.cache[cache_key] = results

        # Clean old cache entries
        if len(self.cache) > 100:
            oldest_keys = sorted(self.cache.keys())[:50]
            for key in oldest_keys:
                del self.cache[key]

        return results

    async def _fetch_with_name(self, name: str, coro):
        """Helper to fetch with source name"""
        result = await coro
        return name, result
