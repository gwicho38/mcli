"""
LSH API Client for mcli
Provides integration with LSH daemon API server for data pipeline processing
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
import aiomqtt
from aiohttp_sse_client import client as sse_client

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class LSHClient:
    """Client for connecting to LSH daemon API server"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = base_url or os.getenv("LSH_API_URL", "http://localhost:3030")
        self.api_key = api_key or os.getenv("LSH_API_KEY")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self._event_handlers: Dict[str, List[Callable]] = {}

        if not self.api_key:
            logger.warning("LSH_API_KEY not set - authentication may fail")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self):
        """Initialize aiohttp session"""
        if not self.session:
            connector = aiohttp.TCPConnector(limit=10)
            self.session = aiohttp.ClientSession(connector=connector, timeout=self.timeout)
            logger.info(f"Connected to LSH API at {self.base_url}")

    async def disconnect(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from LSH API")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to LSH API"""
        if not self.session:
            await self.connect()

        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers()

        try:
            async with self.session.request(method, url, headers=headers, json=data) as response:
                if response.status == 401:
                    raise ValueError("LSH API authentication failed - check API key")

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"LSH API request failed: {e}")
            raise

    # Job Management
    async def get_status(self) -> Dict[str, Any]:
        """Get LSH daemon status"""
        return await self._request("GET", "/api/status")

    async def list_jobs(self, filter_params: Optional[Dict] = None) -> List[Dict]:
        """List all jobs from LSH daemon"""
        endpoint = "/api/jobs"
        if filter_params:
            # Convert filter to query params
            endpoint += "?" + "&".join(f"{k}={v}" for k, v in filter_params.items())
        return await self._request("GET", endpoint)

    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get specific job details"""
        return await self._request("GET", f"/api/jobs/{job_id}")

    async def create_job(self, job_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job in LSH daemon"""
        return await self._request("POST", "/api/jobs", job_spec)

    async def trigger_job(self, job_id: str) -> Dict[str, Any]:
        """Trigger job execution"""
        return await self._request("POST", f"/api/jobs/{job_id}/trigger")

    async def start_job(self, job_id: str) -> Dict[str, Any]:
        """Start a job"""
        return await self._request("POST", f"/api/jobs/{job_id}/start")

    async def stop_job(self, job_id: str, signal: str = "SIGTERM") -> Dict[str, Any]:
        """Stop a job"""
        return await self._request("POST", f"/api/jobs/{job_id}/stop", {"signal": signal})

    async def remove_job(self, job_id: str, force: bool = False) -> None:
        """Remove a job"""
        params = {"force": str(force).lower()}
        endpoint = f"/api/jobs/{job_id}?" + "&".join(f"{k}={v}" for k, v in params.items())
        await self._request("DELETE", endpoint)

    async def bulk_create_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple jobs"""
        return await self._request("POST", "/api/jobs/bulk", {"jobs": jobs})

    # Data Export
    async def export_jobs(self, format: str = "json") -> str:
        """Export job data"""
        endpoint = f"/api/export/jobs?format={format}"
        return await self._request("GET", endpoint)

    # Webhook Management
    async def list_webhooks(self) -> Dict[str, Any]:
        """List configured webhooks"""
        return await self._request("GET", "/api/webhooks")

    async def add_webhook(self, endpoint_url: str) -> Dict[str, Any]:
        """Add webhook endpoint"""
        return await self._request("POST", "/api/webhooks", {"endpoint": endpoint_url})

    # Event Handling
    def on(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event: {event_type}")

    async def _emit_event(self, event_type: str, data: Any):
        """Emit event to registered handlers"""
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")

    async def stream_events(self):
        """Stream events from LSH API using Server-Sent Events"""
        if not self.session:
            await self.connect()

        url = urljoin(self.base_url, "/api/events")
        headers = self._get_headers()

        logger.info("Starting LSH event stream...")

        try:
            async with sse_client.EventSource(
                url, session=self.session, headers=headers
            ) as event_source:
                async for event in event_source:
                    try:
                        if event.data.strip():
                            data = json.loads(event.data)
                            event_type = data.get("type", "unknown")

                            logger.debug(f"Received LSH event: {event_type}")

                            # Emit to registered handlers
                            await self._emit_event(event_type, data)
                            await self._emit_event("*", data)  # Wildcard handler

                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse SSE data: {e}")
                    except Exception as e:
                        logger.error(f"Error processing SSE event: {e}")

        except Exception as e:
            logger.error(f"SSE connection error: {e}")
            raise

    # Supabase Integration
    async def trigger_supabase_sync(
        self, table: str, operation: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger Supabase data sync notification"""
        payload = {"table": table, "operation": operation, "data": data}
        return await self._request("POST", "/api/supabase/sync", payload)

    # Health Check
    async def health_check(self) -> bool:
        """Check if LSH API is healthy"""
        try:
            if not self.session:
                await self.connect()

            url = urljoin(self.base_url, "/health")
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class LSHEventProcessor:
    """Process events from LSH daemon for data pipeline integration"""

    def __init__(self, lsh_client: LSHClient):
        self.client = lsh_client
        self.logger = get_logger(f"{__name__}.processor")
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Setup default event handlers"""
        self.client.on("job:completed", self._handle_job_completed)
        self.client.on("job:failed", self._handle_job_failed)
        self.client.on("job:started", self._handle_job_started)
        self.client.on("supabase:sync", self._handle_supabase_sync)
        self.client.on("connected", self._handle_connected)

    async def _handle_connected(self, data: Dict[str, Any]):
        """Handle connection established event"""
        self.logger.info("Connected to LSH event stream")

    async def _handle_job_started(self, data: Dict[str, Any]):
        """Handle job started event"""
        job_data = data.get("data", {})
        job_id = job_data.get("id", "unknown")
        job_name = job_data.get("name", "unknown")

        self.logger.info(f"LSH job started: {job_name} ({job_id})")

        # Emit mcli-specific event
        await self._emit_mcli_event(
            "lsh.job.started",
            {
                "job_id": job_id,
                "job_name": job_name,
                "timestamp": data.get("timestamp"),
                "job_data": job_data,
            },
        )

    async def _handle_job_completed(self, data: Dict[str, Any]):
        """Handle job completion event"""
        job_data = data.get("data", {})
        job_id = job_data.get("id", "unknown")
        job_name = job_data.get("name", "unknown")

        self.logger.info(f"LSH job completed: {job_name} ({job_id})")

        # Process job output if available
        stdout = job_data.get("stdout", "")
        stderr = job_data.get("stderr", "")

        # Check if this is a politician trading job
        if "politician" in job_name.lower() or "trading" in job_name.lower():
            await self._process_trading_data(job_data, stdout)

        # Check if this is a Supabase sync job
        if "supabase" in job_name.lower() or job_data.get("databaseSync"):
            await self._process_supabase_job(job_data)

        # Emit mcli-specific event
        await self._emit_mcli_event(
            "lsh.job.completed",
            {
                "job_id": job_id,
                "job_name": job_name,
                "timestamp": data.get("timestamp"),
                "job_data": job_data,
                "stdout": stdout,
                "stderr": stderr,
            },
        )

    async def _handle_job_failed(self, data: Dict[str, Any]):
        """Handle job failure event"""
        job_data = data.get("data", {})
        job_id = job_data.get("id", "unknown")
        job_name = job_data.get("name", "unknown")
        error = job_data.get("error", "Unknown error")

        self.logger.error(f"LSH job failed: {job_name} ({job_id}) - {error}")

        # Emit mcli-specific event
        await self._emit_mcli_event(
            "lsh.job.failed",
            {
                "job_id": job_id,
                "job_name": job_name,
                "timestamp": data.get("timestamp"),
                "error": error,
                "job_data": job_data,
            },
        )

    async def _handle_supabase_sync(self, data: Dict[str, Any]):
        """Handle Supabase data sync event"""
        table = data.get("table", "unknown")
        operation = data.get("operation", "unknown")
        sync_data = data.get("data", {})

        self.logger.info(f"Supabase sync: {operation} on {table}")

        # Process based on table type
        if "politician" in table.lower() or "trading" in table.lower():
            await self._process_politician_data(table, operation, sync_data)

        # Emit mcli-specific event
        await self._emit_mcli_event(
            "lsh.supabase.sync",
            {
                "table": table,
                "operation": operation,
                "data": sync_data,
                "timestamp": data.get("timestamp"),
            },
        )

    async def _process_trading_data(self, job_data: Dict, stdout: str):
        """Process politician trading data from job output"""
        try:
            # Parse trading data from stdout
            if stdout.strip():
                # Assuming JSON output format
                trading_records = []
                for line in stdout.strip().split("\n"):
                    try:
                        record = json.loads(line)
                        trading_records.append(record)
                    except json.JSONDecodeError:
                        continue

                if trading_records:
                    self.logger.info(f"Processed {len(trading_records)} trading records")

                    # Emit processed data event
                    await self._emit_mcli_event(
                        "trading.data.processed",
                        {
                            "records": trading_records,
                            "count": len(trading_records),
                            "job_id": job_data.get("id"),
                            "timestamp": time.time(),
                        },
                    )

        except Exception as e:
            self.logger.error(f"Error processing trading data: {e}")

    async def _process_supabase_job(self, job_data: Dict):
        """Process Supabase synchronization job"""
        try:
            # Check for database sync metadata
            sync_info = job_data.get("databaseSync", {})

            self.logger.info(f"Processing Supabase sync job: {job_data.get('name')}")

            # Emit database sync event
            await self._emit_mcli_event(
                "database.sync.completed",
                {"job_id": job_data.get("id"), "sync_info": sync_info, "timestamp": time.time()},
            )

        except Exception as e:
            self.logger.error(f"Error processing Supabase job: {e}")

    async def _process_politician_data(self, table: str, operation: str, data: Dict):
        """Process politician-related data changes"""
        try:
            self.logger.info(f"Processing politician data: {operation} on {table}")

            # Apply data transformations based on operation
            processed_data = await self._transform_politician_data(table, operation, data)

            # Emit transformed data event
            await self._emit_mcli_event(
                "politician.data.updated",
                {
                    "table": table,
                    "operation": operation,
                    "original_data": data,
                    "processed_data": processed_data,
                    "timestamp": time.time(),
                },
            )

        except Exception as e:
            self.logger.error(f"Error processing politician data: {e}")

    async def _transform_politician_data(self, table: str, operation: str, data: Dict) -> Dict:
        """Transform politician data based on business rules"""
        # Apply transformations here
        transformed = data.copy()

        # Add computed fields
        if "transaction_amount" in data:
            amount = data["transaction_amount"]
            if isinstance(amount, (int, float)):
                transformed["amount_category"] = self._categorize_amount(amount)

        # Add timestamps
        transformed["processed_at"] = time.time()
        transformed["mcli_version"] = "1.0.0"

        return transformed

    def _categorize_amount(self, amount: float) -> str:
        """Categorize transaction amounts"""
        if amount < 1000:
            return "small"
        elif amount < 50000:
            return "medium"
        elif amount < 500000:
            return "large"
        else:
            return "very_large"

    async def _emit_mcli_event(self, event_type: str, data: Dict[str, Any]):
        """Emit mcli-specific events (can be extended to use message queue)"""
        self.logger.debug(f"Emitting mcli event: {event_type}")
        # For now, just log - can be extended to use Redis, RabbitMQ, etc.

    async def start_processing(self):
        """Start processing LSH events"""
        self.logger.info("Starting LSH event processing...")
        await self.client.stream_events()
