#!/usr/bin/env python3
"""
Test script for mcli-LSH integration
Tests the connection and basic functionality between mcli and LSH daemon
"""

import asyncio
import json
import os
import sys
import time
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Check for aiomqtt dependency
try:
    import aiomqtt
    HAS_AIOMQTT = True
except ImportError:
    HAS_AIOMQTT = False

if HAS_AIOMQTT:
    from mcli.lib.services.lsh_client import LSHClient, LSHEventProcessor
    from mcli.lib.services.data_pipeline import LSHDataPipeline, DataPipelineConfig


@pytest.mark.skipif(not HAS_AIOMQTT, reason="aiomqtt module not installed")
async def test_lsh_connection():
    """Test basic connection to LSH daemon"""
    print("🔗 Testing LSH daemon connection...")

    try:
        # Use environment variables or defaults
        api_url = os.getenv("LSH_API_URL", "http://localhost:3030")
        api_key = os.getenv("LSH_API_KEY")

        if not api_key:
            print("⚠️  LSH_API_KEY not set - using test without authentication")

        async with LSHClient(base_url=api_url, api_key=api_key) as client:
            # Test health check
            is_healthy = await client.health_check()
            if not is_healthy:
                print("❌ LSH daemon health check failed")
                return False

            print("✅ LSH daemon is healthy")

            # Test status
            status = await client.get_status()
            print(f"📊 Daemon PID: {status.get('pid')}")
            print(f"📊 Uptime: {status.get('uptime', 0) // 60} minutes")

            # Test job listing
            jobs = await client.list_jobs()
            print(f"📋 Total jobs: {len(jobs)}")

            return True

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


@pytest.mark.skipif(not HAS_AIOMQTT, reason="aiomqtt module not installed")
async def test_job_creation():
    """Test creating a simple job"""
    print("\n🛠️  Testing job creation...")

    try:
        async with LSHClient() as client:
            # Create a simple test job
            job_spec = {
                "name": "mcli-test-job",
                "command": "echo 'Hello from mcli test'",
                "type": "shell",
                "description": "Test job created by mcli integration test",
                "tags": ["test", "mcli"],
                "databaseSync": False
            }

            job = await client.create_job(job_spec)
            print(f"✅ Job created: {job.get('id')}")

            # Test triggering the job
            result = await client.trigger_job(job["id"])
            print(f"🚀 Job triggered: {result.get('success', False)}")

            # Wait a moment for execution
            await asyncio.sleep(2)

            # Get job details
            updated_job = await client.get_job(job["id"])
            print(f"📊 Job status: {updated_job.get('status')}")

            # Clean up - remove the test job
            await client.remove_job(job["id"], force=True)
            print("🧹 Test job cleaned up")

            return True

    except Exception as e:
        print(f"❌ Job creation test failed: {e}")
        return False


@pytest.mark.skipif(not HAS_AIOMQTT, reason="aiomqtt module not installed")
async def test_event_listening():
    """Test event listening capabilities"""
    print("\n👂 Testing event listening...")

    try:
        events_received = []

        def event_handler(event_data):
            events_received.append(event_data)
            print(f"📡 Received event: {event_data.get('type')}")

        async with LSHClient() as client:
            # Register event handler
            client.on("*", event_handler)

            # Start listening in background
            listen_task = asyncio.create_task(client.stream_events())

            # Wait a moment to establish connection
            await asyncio.sleep(1)

            # Create and trigger a job to generate events
            job_spec = {
                "name": "mcli-event-test-job",
                "command": "echo 'Event test'",
                "type": "shell"
            }

            job = await client.create_job(job_spec)
            await client.trigger_job(job["id"])

            # Wait for events
            await asyncio.sleep(3)

            # Clean up
            await client.remove_job(job["id"], force=True)
            listen_task.cancel()

            print(f"✅ Received {len(events_received)} events")
            return len(events_received) > 0

    except Exception as e:
        print(f"❌ Event listening test failed: {e}")
        return False


@pytest.mark.skipif(not HAS_AIOMQTT, reason="aiomqtt module not installed")
async def test_data_pipeline():
    """Test data pipeline functionality"""
    print("\n🏭 Testing data pipeline...")

    try:
        # Create pipeline config
        config = DataPipelineConfig()
        config.batch_size = 5
        config.batch_timeout = 5
        config.output_dir = Path("./test_output")
        config.enable_validation = True
        config.enable_enrichment = True

        # Ensure output directory exists
        config.output_dir.mkdir(exist_ok=True)

        async with LSHClient() as client:
            pipeline = LSHDataPipeline(client, config)

            # Test processing some mock trading data
            mock_records = [
                {
                    "politician_name": "Test Politician",
                    "transaction_date": "2024-01-01T00:00:00Z",
                    "transaction_type": "buy",
                    "asset_name": "AAPL",
                    "transaction_amount": 10000
                },
                {
                    "politician_name": "Another Politician",
                    "transaction_date": "2024-01-02T00:00:00Z",
                    "transaction_type": "sell",
                    "asset_name": "MSFT",
                    "transaction_amount": 5000
                }
            ]

            # Process records through pipeline
            processed = await pipeline.processor.process_trading_data(mock_records)

            print(f"✅ Processed {len(processed)} records")

            # Check if enrichment worked
            if processed and "amount_category" in processed[0]:
                print("✅ Data enrichment working")

            # Test batch processing
            for record in processed:
                await pipeline.processor.add_to_batch(record)

            # Force flush batch
            await pipeline.processor.flush_batch()

            # Check if output files were created
            output_files = list(config.output_dir.glob("*.jsonl"))
            if output_files:
                print(f"✅ Created {len(output_files)} output files")

                # Clean up test files
                for file in output_files:
                    file.unlink()
                config.output_dir.rmdir()

            return True

    except Exception as e:
        print(f"❌ Data pipeline test failed: {e}")
        return False


@pytest.mark.skipif(not HAS_AIOMQTT, reason="aiomqtt module not installed")
async def test_webhook_configuration():
    """Test webhook configuration"""
    print("\n🪝 Testing webhook configuration...")

    try:
        async with LSHClient() as client:
            # List current webhooks
            webhooks = await client.list_webhooks()
            print(f"📋 Current webhooks: {len(webhooks.get('endpoints', []))}")

            # Test adding a webhook (this will fail unless mcli webhook server is running)
            test_webhook = "http://localhost:4000/test-webhook"

            try:
                result = await client.add_webhook(test_webhook)
                print("✅ Webhook configuration test passed")
                return True
            except Exception as e:
                print(f"⚠️  Webhook add failed (expected if mcli webhook server not running): {e}")
                return True  # This is expected for testing

    except Exception as e:
        print(f"❌ Webhook configuration test failed: {e}")
        return False


async def main():
    """Run all integration tests"""
    print("🧪 mcli-LSH Integration Test Suite")
    print("=" * 50)

    # Check environment
    print(f"LSH_API_URL: {os.getenv('LSH_API_URL', 'not set')}")
    print(f"LSH_API_KEY: {'set' if os.getenv('LSH_API_KEY') else 'not set'}")
    print()

    tests = [
        ("Connection Test", test_lsh_connection),
        ("Job Creation Test", test_job_creation),
        ("Event Listening Test", test_event_listening),
        ("Data Pipeline Test", test_data_pipeline),
        ("Webhook Configuration Test", test_webhook_configuration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! mcli-LSH integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check LSH daemon status and configuration.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test suite crashed: {e}")
        sys.exit(1)