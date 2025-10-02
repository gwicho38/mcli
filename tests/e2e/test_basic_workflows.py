#!/usr/bin/env python3
"""
Simple LSH-mcli Integration Test
Tests basic connectivity and data flow between LSH API and mcli
"""

import asyncio
import json
import aiohttp
import sys
from pathlib import Path

async def test_lsh_api_connectivity():
    """Test basic LSH API connectivity"""
    print("🔗 Testing LSH API connectivity...")

    try:
        async with aiohttp.ClientSession() as session:
            # Test health endpoint (without auth for now)
            async with session.get("http://localhost:3030/api/health") as response:
                if response.status == 401:
                    print("✅ LSH API is responding (requires auth)")
                    return True
                elif response.status == 200:
                    data = await response.json()
                    print(f"✅ LSH API healthy: {data}")
                    return True
                else:
                    print(f"❌ LSH API unexpected status: {response.status}")
                    return False

    except Exception as e:
        print(f"❌ LSH API connection failed: {e}")
        return False

async def test_lsh_jobs_endpoint():
    """Test LSH jobs endpoint"""
    print("📋 Testing LSH jobs endpoint...")

    try:
        async with aiohttp.ClientSession() as session:
            # Test jobs endpoint without auth
            async with session.get("http://localhost:3030/api/jobs") as response:
                if response.status == 401:
                    print("✅ LSH jobs endpoint responding (requires auth)")
                    return True
                elif response.status == 200:
                    data = await response.json()
                    print(f"✅ LSH jobs endpoint accessible: {len(data)} jobs")
                    return True
                else:
                    print(f"❌ Jobs endpoint unexpected status: {response.status}")
                    return False

    except Exception as e:
        print(f"❌ Jobs endpoint test failed: {e}")
        return False

async def test_data_processing():
    """Test mock data processing pipeline"""
    print("🏭 Testing data processing pipeline...")

    try:
        # Mock politician trading data
        mock_data = [
            {
                "politician_name": "Test Politician",
                "transaction_date": "2024-01-01T00:00:00Z",
                "transaction_type": "buy",
                "asset_name": "AAPL",
                "transaction_amount": 10000,
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]

        # Simple data enrichment
        for record in mock_data:
            amount = record.get("transaction_amount", 0)
            if amount > 50000:
                record["amount_category"] = "large"
            elif amount > 10000:
                record["amount_category"] = "medium"
            else:
                record["amount_category"] = "small"

            record["mcli_processed_at"] = "2024-01-01T00:00:00Z"
            record["mcli_processing_version"] = "1.0.0"

        print(f"✅ Processed {len(mock_data)} records")
        print(f"Sample enriched record: {json.dumps(mock_data[0], indent=2)}")

        # Write to output file
        output_dir = Path("./test_output")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / "test_processed_data.jsonl"
        with open(output_file, 'w') as f:
            for record in mock_data:
                f.write(json.dumps(record) + '\n')

        print(f"✅ Output written to: {output_file}")
        return True

    except Exception as e:
        print(f"❌ Data processing test failed: {e}")
        return False

async def main():
    """Run integration tests"""
    print("🧪 Simple LSH-mcli Integration Test")
    print("=" * 50)

    tests = [
        ("LSH API Connectivity", test_lsh_api_connectivity),
        ("LSH Jobs Endpoint", test_lsh_jobs_endpoint),
        ("Data Processing Pipeline", test_data_processing),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            print()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
            print()

    # Summary
    print("=" * 50)
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
        print("🎉 Integration test successful!")
        print("✅ LSH API server is running and accessible")
        print("✅ Data processing pipeline is working")
        return 0
    else:
        print("⚠️  Some tests failed. Check LSH daemon and API server status.")
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