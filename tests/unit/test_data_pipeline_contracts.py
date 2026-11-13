"""Pipeline validation, immutable enrichment, batching and event input boundaries."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from mcli.lib.services.data_pipeline import DataPipelineConfig, DataProcessor, LSHDataPipeline

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def record(amount=12000):
    return {
        "politician_name": "fixture person",
        "transaction_date": "2026-11-13",
        "transaction_type": "buy",
        "asset_name": "fixture",
        "transaction_amount": amount,
    }


@pytest.fixture
def processor(tmp_path):
    config = DataPipelineConfig()
    config.output_dir = tmp_path / "processed"
    config.batch_size = 2
    return DataProcessor(config)


@pytest.mark.parametrize(
    "amount,category,bucket",
    [
        (999, "micro", "0-1K"),
        (1000, "small", "1K-10K"),
        (12000, "small", "10K-50K"),
        (15000, "medium", "10K-50K"),
        (50000, "large", "50K-100K"),
        (100000, "large", "100K-500K"),
        (500000, "mega", "500K-1M"),
        (1000000, "mega", "1M+"),
    ],
)
async def test_enrichment_boundaries_preserve_original_record(processor, amount, category, bucket):
    original = record(amount)
    result = await processor.process_trading_data([original])
    assert len(result) == 1
    enriched = result[0]
    assert enriched["amount_category"] == category and enriched["amount_bucket"] == bucket
    assert enriched["politician_metadata"]["name_normalized"] == "Fixture Person"
    assert enriched["market_context"]["asset_normalized"] == "FIXTURE"
    assert "mcli_processed_at" in enriched and "processed_at" not in original


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {**record(), "transaction_date": "invalid"},
        {**record(), "transaction_amount": None},
        {**record(), "transaction_amount": "invalid"},
    ],
)
async def test_invalid_records_are_rejected_without_poisoning_valid_neighbors(processor, bad):
    result = await processor.process_trading_data([bad, record()])
    assert len(result) == 1 and result[0]["politician_name"] == "fixture person"


async def test_validation_and_enrichment_can_be_disabled(processor):
    processor.config.enable_validation = False
    processor.config.enable_enrichment = False
    result = await processor.process_trading_data([{"id": "unvalidated"}])
    assert result[0]["id"] == "unvalidated"
    assert "politician_metadata" not in result[0]


@pytest.mark.parametrize(
    "table,data,expected",
    [
        (
            "politicians",
            {"id": 1, "name": "fixture", "party": "ind"},
            {"name_normalized": "Fixture", "party_normalized": "IND"},
        ),
        (
            "trading",
            {"id": 1, "asset_name": "stock", "amount": "12.5"},
            {"asset_name_normalized": "STOCK", "amount_float": 12.5},
        ),
        ("trading", {"id": 1, "amount": "unknown"}, {}),
        ("other", {"id": 1}, {}),
    ],
)
async def test_table_transformations_preserve_input(processor, table, data, expected):
    original = data.copy()
    transformed = await processor.process_supabase_sync(table, "INSERT", data)
    assert all(transformed[key] == value for key, value in expected.items())
    assert transformed["mcli_source_table"] == table and transformed["mcli_operation"] == "INSERT"
    assert data == original
    assert await processor.process_supabase_sync(table, "INSERT", {}) == {}
    assert await processor.process_supabase_sync(table, "INSERT", {"id": None}) == {}


async def test_batch_threshold_flush_and_retry_preserve_records(processor):
    await processor.add_to_batch(record(1))
    assert len(processor.batch_buffer) == 1 and list(processor.config.output_dir.iterdir()) == []
    await processor.add_to_batch(record(2))
    files = list(processor.config.output_dir.glob("*.jsonl"))
    assert len(files) == 1
    saved = [json.loads(line) for line in files[0].read_text().splitlines()]
    assert [r["transaction_amount"] for r in saved] == [1, 2]
    assert processor.batch_buffer == []
    await processor.flush_batch()
    processor._save_batch = AsyncMock(side_effect=RuntimeError("temporary write error"))
    await processor.add_to_batch(record(3))
    await processor.flush_batch()
    assert [r["transaction_amount"] for r in processor.batch_buffer] == [3]
    processor._save_batch = AsyncMock()
    await processor.flush_batch()
    assert processor.batch_buffer == []
    assert processor._save_batch.call_args.args[0][0]["transaction_amount"] == 3


async def test_pipeline_job_events_ignore_non_json_and_emit_stats(processor):
    client = Mock()
    client.stream_events = AsyncMock(side_effect=RuntimeError("transport disconnected"))
    pipeline = LSHDataPipeline(client, processor.config)
    registered = {call.args[0]: call.args[1] for call in client.on.call_args_list}
    assert {"lsh.job.completed", "lsh.supabase.sync", "trading.data.processed"} <= registered.keys()
    pipeline.processor.config.batch_size = 100
    output = "not json\n\n" + json.dumps(record())
    await registered["lsh.job.completed"](
        {"job_name": "fixture trading", "job_id": "job-42", "stdout": output}
    )
    assert pipeline.processor.batch_buffer[0]["source_job_id"] == "job-42"
    await registered["lsh.job.completed"]({"job_name": "unrelated", "stdout": output})
    assert len(pipeline.processor.batch_buffer) == 1
    await registered["trading.data.processed"]({"records": [record()]})
    assert (await pipeline.get_stats())["batch_buffer_size"] == 2
    with pytest.raises(RuntimeError, match="transport disconnected"):
        await pipeline.start()
    assert (await pipeline.get_stats())["is_running"] is False
    pipeline._is_running = True
    await pipeline.start()
    assert client.stream_events.await_count == 1
    await pipeline.stop()
    assert pipeline.processor.batch_buffer == []
    await pipeline.stop()
