"""Search ranking and caching with real sklearn vectors and a local async cache double."""

import fnmatch
from unittest.mock import AsyncMock

import numpy as np
import pytest

from mcli.lib.search import cached_vectorizer as search

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
async def vectorizer(monkeypatch):
    monkeypatch.setattr(search, "REDIS_AVAILABLE", False)
    vectorizer = search.CachedTfIdfVectorizer(use_rust=False)
    await vectorizer.initialize()
    yield vectorizer
    await vectorizer.close()


async def test_similarity_ranking_zero_vectors_and_batch_order(vectorizer):
    documents = ["electric vehicle charging", "database backup restore", "vehicle charging station"]
    with pytest.raises(ValueError, match="must be fitted"):
        await vectorizer.transform(["vehicle"])
    result = await vectorizer.similarity_search("database backup", documents, top_k=2)
    assert result[0][0] == 1 and result[0][1] > 0.5
    assert len(result) == 2
    zero = await vectorizer.transform(["zzzzunknownword"])
    assert np.all(zero == 0)
    results = await vectorizer.batch_similarity_search(
        ["database backup", "charging station"], documents, top_k=1
    )
    assert [rows[0][0] for rows in results] == [1, 2]
    assert vectorizer._cosine_similarity(zero[0], zero[0]) == 0
    await vectorizer.warm_cache(documents, ["vehicle", "backup"])
    stats = await vectorizer.get_cache_stats()
    assert stats["cache_misses"] > 0 and stats["redis_connected"] is False


async def test_cache_roundtrips_arrays_rankings_and_clears_only_its_prefix(vectorizer):
    values = {"other:keep": b"unrelated"}
    cache = AsyncMock()
    cache.get.side_effect = lambda key: values.get(key)

    def setex(key, ttl, value):
        assert ttl == 3600
        values[key] = value

    cache.setex.side_effect = setex
    cache.keys.side_effect = lambda pattern: [
        key for key in values if fnmatch.fnmatch(key, pattern)
    ]
    cache.delete.side_effect = lambda *keys: [values.pop(key) for key in keys]
    cache.info.return_value = {"used_memory_human": "1K"}
    vectorizer.redis_client = cache
    documents = ["charging electric vehicles", "database backup", "charging station"]
    first = await vectorizer.fit_transform(documents)
    second = await vectorizer.fit_transform(documents)
    np.testing.assert_allclose(first, second)
    first_transform = await vectorizer.transform(["charging"])
    np.testing.assert_allclose(first_transform, await vectorizer.transform(["charging"]))
    first_rank = await vectorizer.similarity_search("backup", documents, 1)
    assert first_rank[0][0] == 1
    assert await vectorizer.similarity_search("backup", documents, 1) == first_rank
    batch = await vectorizer.batch_similarity_search(["backup", "electric"], documents, 1)
    assert [rows[0][0] for rows in batch] == [1, 0]
    assert await vectorizer.batch_similarity_search(["backup", "electric"], documents, 1) == batch
    stats = await vectorizer.get_cache_stats()
    assert stats["cache_hits"] >= 5 and stats["cached_entries"] > 0
    assert stats["redis_memory_used"] == "1K" and stats["hit_rate"] > 0
    await vectorizer.clear_cache("does-not-match")
    assert len(values) > 1
    await vectorizer.clear_cache()
    assert values == {"other:keep": b"unrelated"}


async def test_cache_transport_failures_do_not_break_search(vectorizer):
    cache = AsyncMock()
    for operation in (cache.get, cache.setex, cache.keys, cache.info):
        operation.side_effect = ConnectionError("fixture cache offline")
    vectorizer.redis_client = cache
    results = await vectorizer.similarity_search(
        "backup", ["database backup", "vehicle charging"], 1
    )
    assert results[0][0] == 0
    await vectorizer.clear_cache()
    assert (await vectorizer.get_cache_stats())["redis_connected"] is True


async def test_manager_reuses_domains_and_preserves_command_objects(monkeypatch):
    monkeypatch.setattr(search, "REDIS_AVAILABLE", False)
    manager = search.SmartVectorizerManager()
    first = await manager.get_vectorizer("commands")
    assert await manager.get_vectorizer("commands") is first
    assert await manager.get_vectorizer("other") is not first
    commands = [
        {"name": "backup", "description": "database restore", "tags": ["data"]},
        {"name": "charge", "description": "electric vehicle", "tags": ["energy"]},
    ]
    result = await manager.search_commands("database", commands, 1)
    assert result[0][0] is commands[0] and result[0][1] > 0
    await manager.close_all()
    assert manager.vectorizers == {}
