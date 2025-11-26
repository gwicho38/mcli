"""Unit tests for storage cache module."""

import json
import tempfile
from pathlib import Path

import pytest

from mcli.storage.cache import LocalCache


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache(temp_cache_dir):
    """Create a LocalCache instance with temporary directory."""
    return LocalCache(temp_cache_dir)


class TestLocalCacheInit:
    """Tests for LocalCache initialization."""

    def test_creates_cache_directory(self, temp_cache_dir):
        """Test that cache creates directory if not exists."""
        cache_dir = temp_cache_dir / "new_cache"
        assert not cache_dir.exists()

        cache = LocalCache(cache_dir)
        assert cache_dir.exists()
        assert cache.cache_dir == cache_dir

    def test_loads_existing_metadata(self, temp_cache_dir):
        """Test that existing metadata file is loaded."""
        metadata = {"bafkreitest": {"size": 100, "type": "test"}}
        metadata_file = temp_cache_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata))

        cache = LocalCache(temp_cache_dir)
        assert "bafkreitest" in cache.metadata


class TestGenerateCID:
    """Tests for CID generation."""

    def test_generates_valid_cid_format(self, cache):
        """Test that generated CID has correct format."""
        cid = cache.generate_cid(b"test data")
        assert cid.startswith("bafkrei")
        assert len(cid) == 59  # bafkrei (7) + 52 hex chars

    def test_same_data_same_cid(self, cache):
        """Test that same data produces same CID."""
        data = b"hello world"
        cid1 = cache.generate_cid(data)
        cid2 = cache.generate_cid(data)
        assert cid1 == cid2

    def test_different_data_different_cid(self, cache):
        """Test that different data produces different CID."""
        cid1 = cache.generate_cid(b"data1")
        cid2 = cache.generate_cid(b"data2")
        assert cid1 != cid2


class TestCacheStoreRetrieve:
    """Tests for store and retrieve operations."""

    @pytest.mark.asyncio
    async def test_store_creates_file(self, cache):
        """Test that store creates data file."""
        data = b"test data"
        cid = "bafkreitestcid12345678901234567890123456789012345678"

        result = await cache.store(cid, data, {"type": "test"})
        assert result is True

        cache_file = cache.cache_dir / f"{cid}.data"
        assert cache_file.exists()
        assert cache_file.read_bytes() == data

    @pytest.mark.asyncio
    async def test_retrieve_returns_data(self, cache):
        """Test that retrieve returns stored data."""
        data = b"test data"
        cid = "bafkreitestcid12345678901234567890123456789012345678"

        await cache.store(cid, data, {})
        retrieved = await cache.retrieve(cid)

        assert retrieved == data

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_returns_none(self, cache):
        """Test that retrieve returns None for nonexistent CID."""
        result = await cache.retrieve("bafkreinonexistent123456789012345678901234567890123")
        assert result is None

    @pytest.mark.asyncio
    async def test_store_updates_metadata(self, cache):
        """Test that store updates metadata."""
        data = b"test data"
        cid = "bafkreitestcid12345678901234567890123456789012345678"
        metadata = {"type": "test", "version": "1.0"}

        await cache.store(cid, data, metadata)

        assert cid in cache.metadata
        assert cache.metadata[cid]["type"] == "test"
        assert cache.metadata[cid]["size"] == len(data)
        assert "cached_at" in cache.metadata[cid]


class TestCacheDelete:
    """Tests for delete operation."""

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, cache):
        """Test that delete removes data file."""
        cid = "bafkreitestcid12345678901234567890123456789012345678"
        await cache.store(cid, b"test", {})

        result = await cache.delete(cid)
        assert result is True

        cache_file = cache.cache_dir / f"{cid}.data"
        assert not cache_file.exists()

    @pytest.mark.asyncio
    async def test_delete_removes_metadata(self, cache):
        """Test that delete removes metadata entry."""
        cid = "bafkreitestcid12345678901234567890123456789012345678"
        await cache.store(cid, b"test", {})

        await cache.delete(cid)
        assert cid not in cache.metadata

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_true(self, cache):
        """Test that deleting nonexistent entry returns True."""
        result = await cache.delete("bafkreinonexistent123456789012345678901234567890123")
        assert result is True


class TestCacheMetadata:
    """Tests for metadata operations."""

    @pytest.mark.asyncio
    async def test_get_metadata_returns_dict(self, cache):
        """Test that get_metadata returns metadata dict."""
        cid = "bafkreitestcid12345678901234567890123456789012345678"
        await cache.store(cid, b"test", {"type": "test"})

        metadata = await cache.get_metadata(cid)
        assert metadata is not None
        assert metadata["type"] == "test"

    @pytest.mark.asyncio
    async def test_get_metadata_nonexistent_returns_none(self, cache):
        """Test that get_metadata returns None for unknown CID."""
        result = await cache.get_metadata("bafkreinonexistent12345678901234567890123456789012")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_metadata_merges(self, cache):
        """Test that update_metadata merges with existing."""
        cid = "bafkreitestcid12345678901234567890123456789012345678"
        await cache.store(cid, b"test", {"type": "test"})

        await cache.update_metadata(cid, {"version": "2.0"})

        metadata = await cache.get_metadata(cid)
        assert metadata["type"] == "test"
        assert metadata["version"] == "2.0"


class TestCacheQuery:
    """Tests for query operations."""

    @pytest.mark.asyncio
    async def test_query_metadata_with_filter(self, cache):
        """Test query with filters."""
        await cache.store("bafkreicid1" + "0" * 46, b"test1", {"type": "a"})
        await cache.store("bafkreicid2" + "0" * 46, b"test2", {"type": "b"})
        await cache.store("bafkreicid3" + "0" * 46, b"test3", {"type": "a"})

        results = await cache.query_metadata({"type": "a"})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_query_metadata_with_limit(self, cache):
        """Test query with limit."""
        for i in range(5):
            cid = f"bafkreicid{i}" + "0" * 46
            await cache.store(cid, b"test", {"type": "test"})

        results = await cache.query_metadata({"type": "test"}, limit=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_all(self, cache):
        """Test list_all returns all CIDs."""
        cids = [f"bafkreicid{i}" + "0" * 46 for i in range(3)]
        for cid in cids:
            await cache.store(cid, b"test", {})

        result = await cache.list_all()
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_all_with_prefix(self, cache):
        """Test list_all with prefix filter."""
        await cache.store("bafkreiabc" + "0" * 46, b"test", {})
        await cache.store("bafkreixyz" + "0" * 46, b"test", {})

        result = await cache.list_all(prefix="bafkreia")
        assert len(result) == 1


class TestCacheStats:
    """Tests for cache statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, cache):
        """Test get_stats on empty cache."""
        stats = cache.get_stats()
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, cache):
        """Test get_stats with cached data."""
        await cache.store("bafkreicid1" + "0" * 46, b"test", {"type": "a"})
        await cache.store("bafkreicid2" + "0" * 46, b"testdata", {"type": "b"})

        stats = cache.get_stats()
        assert stats["total_files"] == 2
        assert stats["total_size_bytes"] == len(b"test") + len(b"testdata")
        assert stats["types"]["a"] == 1
        assert stats["types"]["b"] == 1
