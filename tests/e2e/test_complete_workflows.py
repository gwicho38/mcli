#!/usr/bin/env python3
"""
End-to-End LSH -> mcli Integration Test

NOTE: This test depends on LSH services integration which may not be available.
Tests are skipped pending service dependency verification.
"""

import pytest

# Skip all tests in this module - LSH services integration needs verification
pytestmark = pytest.mark.skip(reason="LSH services integration pending verification")

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


class EndToEndTestRunner:
    """Manages the complete end-to-end integration test"""

    def __init__(self):
        self.test_results = []
        self.processed_records = []
        self.lsh_client = None
        self.pipeline = None
        self.test_job_id = None

    async def setup(self):
        """Setup test environment"""
        print("🔧 Setting up end-to-end test environment...")

        # Configure pipeline for testing
        config = DataPipelineConfig()
        config.batch_size = 1  # Process immediately for testing
        config.batch_timeout = 2  # Short timeout
        config.output_dir = Path("./e2e_test_output")
        config.enable_validation = True
        config.enable_enrichment = True

        # Ensure output directory exists
        config.output_dir.mkdir(exist_ok=True)

        # Initialize LSH client
        api_url = os.getenv("LSH_API_URL", "http://localhost:3030")
        api_key = os.getenv("LSH_API_KEY")

        self.lsh_client = LSHClient(base_url=api_url, api_key=api_key)
        await self.lsh_client.connect()

        # Test connection
        is_healthy = await self.lsh_client.health_check()
        if not is_healthy:
            raise Exception("LSH daemon is not healthy")

        # Initialize data pipeline
        self.pipeline = LSHDataPipeline(self.lsh_client, config)

        # Setup custom event handlers for testing
        self._setup_test_handlers()

        print("✅ Test environment setup complete")

    def _setup_test_handlers(self):
        """Setup custom event handlers for testing"""

        async def handle_job_completed(event_data: Dict[str, Any]):
            """Handle job completion specifically for our test"""
            job_data = event_data.get("data", {})
            job_id = job_data.get("id")
            job_name = job_data.get("name", "")

            # Only process our test job
            if job_id == self.test_job_id and "politician-trading-test" in job_name:
                print(f"🎯 Processing test job completion: {job_name}")

                # Extract and process output
                stdout = job_data.get("stdout", "")
                if stdout.strip():
                    await self._process_test_output(stdout)

        async def handle_trading_data_processed(event_data: Dict[str, Any]):
            """Handle processed trading data"""
            records = event_data.get("records", [])
            self.processed_records.extend(records)
            print(f"📊 Received {len(records)} processed trading records")

        # Register test-specific handlers
        self.lsh_client.on("lsh.job.completed", handle_job_completed)
        self.lsh_client.on("trading.data.processed", handle_trading_data_processed)

    async def _process_test_output(self, output: str):
        """Process job output through mcli pipeline"""
        try:
            print("🏭 Processing job output through mcli pipeline...")

            # Parse output as JSON lines
            records = []
            for line in output.strip().split('\n'):
                if line.strip():
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Failed to parse line: {line[:50]}... - {e}")

            if not records:
                print("⚠️  No valid JSON records found in output")
                return

            print(f"📋 Parsed {len(records)} records from job output")

            # Process through pipeline
            processed_records = await self.pipeline.processor.process_trading_data(records)

            # Add to batch for final processing
            for record in processed_records:
                await self.pipeline.processor.add_to_batch(record)

            # Force batch processing
            await self.pipeline.processor.flush_batch()

            print(f"✅ Successfully processed {len(processed_records)} records")
            self.processed_records.extend(processed_records)

        except Exception as e:
            print(f"❌ Error processing test output: {e}")

    async def create_test_job(self):
        """Create a test job that simulates politician trading data collection"""
        print("🛠️  Creating politician trading test job...")

        # Create a script that outputs realistic politician trading data
        test_script = '''
import json
import random
from datetime import datetime, timedelta

# Simulate politician trading data
politicians = [
    "Nancy Pelosi", "Mitch McConnell", "Chuck Schumer", "Kevin McCarthy"
]

assets = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD"
]

transaction_types = ["buy", "sell"]

# Generate 3 sample records
for i in range(3):
    record = {
        "id": f"trade_{i+1}",
        "politician_name": random.choice(politicians),
        "transaction_date": (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
        "transaction_type": random.choice(transaction_types),
        "asset_name": random.choice(assets),
        "transaction_amount": random.randint(1000, 500000),
        "asset_type": "stock",
        "filing_date": datetime.now().isoformat(),
        "disclosure_source": "senate_disclosures",
        "created_at": datetime.now().isoformat()
    }
    print(json.dumps(record))
'''

        # Create job spec that runs Python script
        job_spec = {
            "name": "politician-trading-test-job",
            "command": f"python3 -c '{test_script}'",
            "type": "shell",
            "description": "Test job for end-to-end integration - generates politician trading data",
            "tags": ["test", "politician-trading", "mcli-integration"],
            "databaseSync": True  # Enable database sync for testing
        }

        try:
            job = await self.lsh_client.create_job(job_spec)
            self.test_job_id = job["id"]
            print(f"✅ Created test job: {self.test_job_id}")
            return job
        except Exception as e:
            print(f"❌ Failed to create test job: {e}")
            raise

    async def trigger_test_job(self):
        """Trigger the test job and wait for completion"""
        if not self.test_job_id:
            raise Exception("No test job created")

        print(f"🚀 Triggering test job: {self.test_job_id}")

        try:
            result = await self.lsh_client.trigger_job(self.test_job_id)
            if not result.get("success", False):
                raise Exception(f"Job trigger failed: {result}")

            print("⏳ Waiting for job completion...")

            # Wait for job to complete (with timeout)
            timeout = 30
            start_time = time.time()

            while time.time() - start_time < timeout:
                job_details = await self.lsh_client.get_job(self.test_job_id)
                status = job_details.get("status", "unknown")

                if status == "completed":
                    print("✅ Job completed successfully")
                    return job_details
                elif status == "failed":
                    error = job_details.get("error", "Unknown error")
                    raise Exception(f"Job failed: {error}")

                await asyncio.sleep(1)

            raise Exception("Job timeout - did not complete within 30 seconds")

        except Exception as e:
            print(f"❌ Job execution failed: {e}")
            raise

    async def start_event_listener(self):
        """Start listening for LSH events"""
        print("👂 Starting LSH event listener...")

        try:
            # Start event streaming in background
            listen_task = asyncio.create_task(self.lsh_client.stream_events())

            # Give listener time to connect
            await asyncio.sleep(2)

            print("✅ Event listener started and connected")
            return listen_task

        except Exception as e:
            print(f"❌ Failed to start event listener: {e}")
            raise

    async def validate_results(self):
        """Validate the end-to-end processing results"""
        print("🔍 Validating end-to-end test results...")

        validation_results = {
            "records_processed": len(self.processed_records) > 0,
            "data_enriched": False,
            "files_created": False,
            "validation_passed": False
        }

        # Check if records were processed
        if self.processed_records:
            print(f"✅ {len(self.processed_records)} records processed")

            # Check if enrichment occurred
            sample_record = self.processed_records[0]
            if "amount_category" in sample_record and "mcli_processed_at" in sample_record:
                validation_results["data_enriched"] = True
                print("✅ Data enrichment successful")

                # Display sample enriched record
                print("📄 Sample enriched record:")
                for key, value in sample_record.items():
                    if key.startswith(("amount_", "mcli_", "politician_")):
                        print(f"   {key}: {value}")

            # Check if validation passed
            if sample_record.get("politician_name") and sample_record.get("transaction_amount"):
                validation_results["validation_passed"] = True
                print("✅ Data validation successful")

        # Check if output files were created
        output_dir = Path("./e2e_test_output")
        output_files = list(output_dir.glob("*.jsonl")) if output_dir.exists() else []

        if output_files:
            validation_results["files_created"] = True
            print(f"✅ {len(output_files)} output files created")

            # Show sample of saved data
            with open(output_files[0], 'r') as f:
                sample_line = f.readline()
                if sample_line:
                    saved_record = json.loads(sample_line)
                    print(f"📁 Saved record contains {len(saved_record)} fields")

        return validation_results

    async def cleanup(self):
        """Clean up test resources"""
        print("🧹 Cleaning up test resources...")

        try:
            # Remove test job
            if self.test_job_id:
                await self.lsh_client.remove_job(self.test_job_id, force=True)
                print("✅ Test job removed")

            # Clean up output files
            output_dir = Path("./e2e_test_output")
            if output_dir.exists():
                for file in output_dir.glob("*"):
                    file.unlink()
                output_dir.rmdir()
                print("✅ Test output files cleaned up")

            # Disconnect client
            if self.lsh_client:
                await self.lsh_client.disconnect()
                print("✅ LSH client disconnected")

        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")

    async def run_complete_test(self):
        """Run the complete end-to-end integration test"""
        print("🚀 Starting Complete End-to-End LSH -> mcli Integration Test")
        print("=" * 70)

        try:
            # Setup
            await self.setup()

            # Start event listener
            listen_task = await self.start_event_listener()

            # Create and trigger test job
            await self.create_test_job()
            job_result = await self.trigger_test_job()

            # Wait for events to be processed
            print("⏳ Waiting for event processing...")
            await asyncio.sleep(5)

            # Cancel event listener
            listen_task.cancel()

            # Validate results
            validation_results = await self.validate_results()

            # Display final results
            print("\n" + "=" * 70)
            print("📊 End-to-End Test Results")
            print("=" * 70)

            all_passed = True
            for check, passed in validation_results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"{check.replace('_', ' ').title()}: {status}")
                if not passed:
                    all_passed = False

            if all_passed:
                print("\n🎉 END-TO-END INTEGRATION SUCCESS!")
                print("✅ LSH successfully pushed data to mcli")
                print("✅ mcli processed data through complete pipeline")
                print("✅ Data was validated, enriched, and saved")
                return True
            else:
                print("\n⚠️  END-TO-END TEST PARTIAL SUCCESS")
                print("Some components worked but integration needs improvement")
                return False

        except Exception as e:
            print(f"\n❌ END-TO-END TEST FAILED: {e}")
            return False

        finally:
            await self.cleanup()


async def main():
    """Main test execution"""
    print("🧪 mcli-LSH End-to-End Integration Test")
    print("This test demonstrates complete data flow from LSH to mcli")
    print()

    # Environment check
    print("🔧 Environment Check:")
    print(f"LSH_API_URL: {os.getenv('LSH_API_URL', 'http://localhost:3030')}")
    print(f"LSH_API_KEY: {'configured' if os.getenv('LSH_API_KEY') else 'not set'}")
    print()

    if not os.getenv("LSH_API_KEY"):
        print("⚠️  Warning: LSH_API_KEY not set. Test may fail if authentication is required.")
        print()

    # Run the test
    runner = EndToEndTestRunner()

    try:
        success = await runner.run_complete_test()
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        await runner.cleanup()
        return 1

    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        await runner.cleanup()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)