"""
Data Pipeline Service for mcli-LSH Integration
Handles ETL processes for data received from LSH daemon
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from mcli.lib.logger.logger import get_logger

from .lsh_client import LSHClient, LSHEventProcessor

logger = get_logger(__name__)


class DataPipelineConfig:
    """Configuration for data pipeline"""

    def __init__(self):
        self.batch_size = 100
        self.batch_timeout = 30  # seconds
        self.retry_attempts = 3
        self.retry_delay = 5  # seconds
        self.output_dir = Path("./data/processed")
        self.enable_validation = True
        self.enable_enrichment = True


class DataValidator:
    """Validates incoming data"""

    def __init__(self):
        self.logger = get_logger(f"{__name__}.validator")

    async def validate_trading_record(self, record: Dict[str, Any]) -> bool:
        """Validate politician trading record"""
        required_fields = [
            "politician_name",
            "transaction_date",
            "transaction_type",
            "asset_name",
        ]

        for field in required_fields:
            if field not in record:
                self.logger.warning(f"Missing required field: {field}")
                return False

        # Validate transaction date
        if "transaction_date" in record:
            try:
                datetime.fromisoformat(record["transaction_date"])
            except ValueError:
                self.logger.warning(f"Invalid transaction date: {record['transaction_date']}")
                return False

        # Validate amount if present
        if "transaction_amount" in record:
            try:
                float(record["transaction_amount"])
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid transaction amount: {record['transaction_amount']}")
                return False

        return True

    async def validate_supabase_record(self, table: str, record: Dict[str, Any]) -> bool:
        """Validate Supabase record based on table schema"""
        if not record:
            return False

        # Basic validation - can be extended with schema validation
        if "id" in record and not record["id"]:
            self.logger.warning("Record missing ID")
            return False

        return True


class DataEnricher:
    """Enriches data with additional information"""

    def __init__(self):
        self.logger = get_logger(f"{__name__}.enricher")

    async def enrich_trading_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich trading record with additional data"""
        enriched = record.copy()

        # Add processing timestamp
        enriched["processed_at"] = datetime.now(timezone.utc).isoformat()

        # Add amount categorization
        if "transaction_amount" in record:
            amount = float(record["transaction_amount"])
            enriched["amount_category"] = self._categorize_amount(amount)
            enriched["amount_bucket"] = self._bucket_amount(amount)

        # Add politician party enrichment (placeholder)
        if "politician_name" in record:
            enriched["politician_metadata"] = await self._get_politician_metadata(
                record["politician_name"]
            )

        # Add market context (placeholder)
        if "asset_name" in record and "transaction_date" in record:
            enriched["market_context"] = await self._get_market_context(
                record["asset_name"], record["transaction_date"]
            )

        return enriched

    def _categorize_amount(self, amount: float) -> str:
        """Categorize transaction amount"""
        if amount < 1000:
            return "micro"
        elif amount < 15000:
            return "small"
        elif amount < 50000:
            return "medium"
        elif amount < 500000:
            return "large"
        else:
            return "mega"

    def _bucket_amount(self, amount: float) -> str:
        """Bucket amounts for analysis"""
        if amount < 1000:
            return "0-1K"
        elif amount < 10000:
            return "1K-10K"
        elif amount < 50000:
            return "10K-50K"
        elif amount < 100000:
            return "50K-100K"
        elif amount < 500000:
            return "100K-500K"
        elif amount < 1000000:
            return "500K-1M"
        else:
            return "1M+"

    async def _get_politician_metadata(self, politician_name: str) -> Dict[str, Any]:
        """Get politician metadata (placeholder for external API)"""
        # This would typically call an external API
        return {
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "source": "mcli_enricher",
            "name_normalized": politician_name.title(),
        }

    async def _get_market_context(self, asset_name: str, transaction_date: str) -> Dict[str, Any]:
        """Get market context for the transaction (placeholder)"""
        # This would typically call financial APIs
        return {
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "asset_normalized": asset_name.upper(),
            "transaction_date": transaction_date,
        }


class DataProcessor:
    """Main data processing engine"""

    def __init__(self, config: DataPipelineConfig):
        self.config = config
        self.logger = get_logger(f"{__name__}.processor")
        self.validator = DataValidator()
        self.enricher = DataEnricher()
        self.batch_buffer: List[Dict[str, Any]] = []
        self.last_batch_time = time.time()
        self._processing_lock = asyncio.Lock()

        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    async def process_trading_data(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process politician trading data"""
        processed_records = []

        for record in records:
            try:
                # Validate
                if self.config.enable_validation:
                    if not await self.validator.validate_trading_record(record):
                        self.logger.warning(
                            f"Validation failed for record: {record.get('id', 'unknown')}"
                        )
                        continue

                # Enrich
                if self.config.enable_enrichment:
                    enriched_record = await self.enricher.enrich_trading_record(record)
                else:
                    enriched_record = record.copy()

                # Add processing metadata
                enriched_record["mcli_processed_at"] = datetime.now(timezone.utc).isoformat()
                enriched_record["mcli_pipeline_version"] = "1.0.0"

                processed_records.append(enriched_record)

            except Exception as e:
                self.logger.error(f"Error processing trading record: {e}")
                continue

        self.logger.info(f"Processed {len(processed_records)}/{len(records)} trading records")
        return processed_records

    async def process_supabase_sync(
        self, table: str, operation: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Supabase sync data"""
        try:
            # Validate
            if self.config.enable_validation:
                if not await self.validator.validate_supabase_record(table, data):
                    self.logger.warning(f"Validation failed for {table} record")
                    return {}

            # Transform based on table and operation
            processed_data = await self._transform_supabase_data(table, operation, data)

            # Add processing metadata
            processed_data["mcli_processed_at"] = datetime.now(timezone.utc).isoformat()
            processed_data["mcli_source_table"] = table
            processed_data["mcli_operation"] = operation

            return processed_data

        except Exception as e:
            self.logger.error(f"Error processing Supabase sync: {e}")
            return {}

    async def _transform_supabase_data(
        self, table: str, operation: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform Supabase data based on table schema"""
        transformed = data.copy()

        # Apply table-specific transformations
        if "politician" in table.lower():
            transformed = await self._transform_politician_table(transformed)
        elif "trading" in table.lower():
            transformed = await self._transform_trading_table(transformed)

        return transformed

    async def _transform_politician_table(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform politician table data"""
        # Normalize names
        if "name" in data:
            data["name_normalized"] = data["name"].title()

        # Add derived fields
        if "party" in data:
            data["party_normalized"] = data["party"].upper()

        return data

    async def _transform_trading_table(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform trading table data"""
        # Normalize asset names
        if "asset_name" in data:
            data["asset_name_normalized"] = data["asset_name"].upper()

        # Convert amounts to float
        if "amount" in data and isinstance(data["amount"], str):
            try:
                data["amount_float"] = float(data["amount"])
            except ValueError:
                pass

        return data

    async def add_to_batch(self, record: Dict[str, Any]):
        """Add record to batch for processing"""
        async with self._processing_lock:
            self.batch_buffer.append(record)

            # Check if batch should be processed
            current_time = time.time()
            time_since_last_batch = current_time - self.last_batch_time

            if (
                len(self.batch_buffer) >= self.config.batch_size
                or time_since_last_batch >= self.config.batch_timeout
            ):
                await self._process_batch()

    async def _process_batch(self):
        """Process accumulated batch"""
        if not self.batch_buffer:
            return

        batch = self.batch_buffer.copy()
        self.batch_buffer.clear()
        self.last_batch_time = time.time()

        self.logger.info(f"Processing batch of {len(batch)} records")

        try:
            # Process batch
            processed_batch = await self.process_trading_data(batch)

            # Save to file
            await self._save_batch(processed_batch)

            # Emit completion event
            await self._emit_batch_completed(processed_batch)

        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            # Re-add to buffer for retry (simplified)
            self.batch_buffer.extend(batch)

    async def _save_batch(self, batch: List[Dict[str, Any]]):
        """Save processed batch to file"""
        if not batch:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processed_batch_{timestamp}.jsonl"
        filepath = self.config.output_dir / filename

        try:
            with open(filepath, "w") as f:
                for record in batch:
                    f.write(json.dumps(record) + "\n")

            self.logger.info(f"Saved {len(batch)} records to {filepath}")

        except Exception as e:
            self.logger.error(f"Failed to save batch: {e}")

    async def _emit_batch_completed(self, batch: List[Dict[str, Any]]):
        """Emit batch completion event"""
        self.logger.info(f"Batch processing completed: {len(batch)} records")

    async def flush_batch(self):
        """Force process current batch"""
        async with self._processing_lock:
            if self.batch_buffer:
                await self._process_batch()


class LSHDataPipeline:
    """Main integration service for LSH-mcli data pipeline"""

    def __init__(self, lsh_client: LSHClient, config: Optional[DataPipelineConfig] = None):
        self.lsh_client = lsh_client
        self.config = config or DataPipelineConfig()
        self.processor = DataProcessor(self.config)
        self.event_processor = LSHEventProcessor(lsh_client)
        self.logger = get_logger(__name__)
        self._is_running = False

        # Setup event handlers
        self._setup_pipeline_handlers()

    def _setup_pipeline_handlers(self):
        """Setup event handlers for pipeline processing"""
        self.lsh_client.on("lsh.job.completed", self._handle_job_completed)
        self.lsh_client.on("lsh.supabase.sync", self._handle_supabase_sync)
        self.lsh_client.on("trading.data.processed", self._handle_trading_data)

    async def _handle_job_completed(self, event_data: Dict[str, Any]):
        """Handle LSH job completion"""
        job_name = event_data.get("job_name", "")
        job_id = event_data.get("job_id", "")

        self.logger.info(f"Processing completed job: {job_name}")

        # Check if this is a trading-related job
        if "trading" in job_name.lower() or "politician" in job_name.lower():
            stdout = event_data.get("stdout", "")
            if stdout.strip():
                await self._process_job_output(job_id, stdout)

    async def _handle_supabase_sync(self, event_data: Dict[str, Any]):
        """Handle Supabase sync event"""
        table = event_data.get("table", "")
        operation = event_data.get("operation", "")
        data = event_data.get("data", {})

        self.logger.info(f"Processing Supabase sync: {operation} on {table}")

        processed_data = await self.processor.process_supabase_sync(table, operation, data)
        if processed_data:
            await self.processor.add_to_batch(processed_data)

    async def _handle_trading_data(self, event_data: Dict[str, Any]):
        """Handle processed trading data"""
        records = event_data.get("records", [])

        self.logger.info(f"Received {len(records)} trading records for pipeline processing")

        for record in records:
            await self.processor.add_to_batch(record)

    async def _process_job_output(self, job_id: str, output: str):
        """Process job output data"""
        try:
            # Parse output lines as JSON
            records = []
            for line in output.strip().split("\n"):
                if line.strip():
                    try:
                        record = json.loads(line)
                        record["source_job_id"] = job_id
                        records.append(record)
                    except json.JSONDecodeError:
                        continue

            if records:
                processed_records = await self.processor.process_trading_data(records)
                for record in processed_records:
                    await self.processor.add_to_batch(record)

        except Exception as e:
            self.logger.error(f"Error processing job output: {e}")

    async def start(self):
        """Start the data pipeline"""
        if self._is_running:
            self.logger.warning("Pipeline already running")
            return

        self.logger.info("Starting LSH data pipeline...")
        self._is_running = True

        try:
            # Start LSH event processing
            await self.event_processor.start_processing()

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            self._is_running = False
            raise

    async def stop(self):
        """Stop the data pipeline"""
        if not self._is_running:
            return

        self.logger.info("Stopping LSH data pipeline...")
        self._is_running = False

        # Flush any remaining batches
        await self.processor.flush_batch()

    async def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            "is_running": self._is_running,
            "batch_buffer_size": len(self.processor.batch_buffer),
            "last_batch_time": self.processor.last_batch_time,
            "config": {
                "batch_size": self.config.batch_size,
                "batch_timeout": self.config.batch_timeout,
                "output_dir": str(self.config.output_dir),
            },
        }
