"""Redis caching layer for ML system"""

import asyncio
import hashlib
import json
import pickle
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Optional, Union

import redis
from redis import asyncio as aioredis

from mcli.ml.config import settings
from mcli.ml.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Manage Redis cache connections and operations"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.async_redis_client: Optional[aioredis.Redis] = None
        self._initialized = False

    def initialize(self):
        """Initialize Redis connections"""
        if self._initialized:
            return

        try:
            # Sync Redis client
            self.redis_client = redis.Redis(
                host=settings.redis.host,
                port=settings.redis.port,
                db=settings.redis.db,
                password=settings.redis.password,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                connection_pool=redis.ConnectionPool(
                    host=settings.redis.host,
                    port=settings.redis.port,
                    db=settings.redis.db,
                    password=settings.redis.password,
                    max_connections=settings.redis.max_connections,
                ),
            )

            # Test connection
            self.redis_client.ping()
            self._initialized = True
            logger.info("Cache manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            self.redis_client = None

    async def initialize_async(self):
        """Initialize async Redis connection"""
        if self.async_redis_client:
            return

        try:
            self.async_redis_client = await aioredis.from_url(
                settings.redis.url,
                encoding="utf-8",
                decode_responses=False,
                max_connections=settings.redis.max_connections,
            )

            # Test connection
            await self.async_redis_client.ping()
            logger.info("Async cache manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize async cache: {e}")
            self.async_redis_client = None

    def _make_key(self, key: str, prefix: str = "mcli:ml:") -> str:
        """Create cache key with prefix"""
        return f"{prefix}{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first (for simple types)
            if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                return json.dumps(value).encode("utf-8")
        except:
            pass

        # Fall back to pickle for complex objects
        return pickle.dumps(value)

    def _deserialize(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        if value is None:
            return None

        # Try JSON first
        try:
            return json.loads(value.decode("utf-8"))
        except:
            pass

        # Fall back to pickle
        try:
            return pickle.loads(value)
        except:
            logger.error("Failed to deserialize cache value")
            return None

    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set cache value"""
        if not self.redis_client:
            self.initialize()

        if not self.redis_client:
            return False

        try:
            cache_key = self._make_key(key)
            serialized_value = self._serialize(value)
            return self.redis_client.setex(cache_key, expire, serialized_value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def get(self, key: str) -> Any:
        """Get cache value"""
        if not self.redis_client:
            self.initialize()

        if not self.redis_client:
            return None

        try:
            cache_key = self._make_key(key)
            value = self.redis_client.get(cache_key)
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set_async(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set cache value asynchronously"""
        if not self.async_redis_client:
            await self.initialize_async()

        if not self.async_redis_client:
            return False

        try:
            cache_key = self._make_key(key)
            serialized_value = self._serialize(value)
            await self.async_redis_client.setex(cache_key, expire, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Async cache set error: {e}")
            return False

    async def get_async(self, key: str) -> Any:
        """Get cache value asynchronously"""
        if not self.async_redis_client:
            await self.initialize_async()

        if not self.async_redis_client:
            return None

        try:
            cache_key = self._make_key(key)
            value = await self.async_redis_client.get(cache_key)
            return self._deserialize(value) if value else None
        except Exception as e:
            logger.error(f"Async cache get error: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete cache entry"""
        if not self.redis_client:
            return False

        try:
            cache_key = self._make_key(key)
            return bool(self.redis_client.delete(cache_key))
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_async(self, key: str) -> bool:
        """Delete cache entry asynchronously"""
        if not self.async_redis_client:
            return False

        try:
            cache_key = self._make_key(key)
            result = await self.async_redis_client.delete(cache_key)
            return bool(result)
        except Exception as e:
            logger.error(f"Async cache delete error: {e}")
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        if not self.redis_client:
            return 0

        try:
            pattern_key = self._make_key(pattern)
            keys = self.redis_client.keys(pattern_key)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Pattern invalidation error: {e}")
            return 0

    def get_or_set(self, key: str, func: Callable, expire: int = 3600) -> Any:
        """Get from cache or compute and set"""
        value = self.get(key)
        if value is not None:
            return value

        value = func()
        self.set(key, value, expire)
        return value

    async def get_or_set_async(self, key: str, func: Callable, expire: int = 3600) -> Any:
        """Get from cache or compute and set asynchronously"""
        value = await self.get_async(key)
        if value is not None:
            return value

        if asyncio.iscoroutinefunction(func):
            value = await func()
        else:
            value = func()

        await self.set_async(key, value, expire)
        return value

    def close(self):
        """Close Redis connections"""
        if self.redis_client:
            self.redis_client.close()
            self.redis_client = None

    async def close_async(self):
        """Close async Redis connection"""
        if self.async_redis_client:
            await self.async_redis_client.close()
            self.async_redis_client = None


# Global cache manager instance
cache_manager = CacheManager()


# Decorator for caching function results
def cached(expire: int = 3600, key_prefix: str = None):
    """Decorator to cache function results"""

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [func.__module__, func.__name__]
            if key_prefix:
                key_parts.insert(0, key_prefix)

            # Add function arguments to key
            key_data = {"args": args, "kwargs": kwargs}
            key_hash = hashlib.md5(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            cache_key = f"{':'.join(key_parts)}:{key_hash}"

            # Try to get from cache
            cached_value = await cache_manager.get_async(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Compute value
            logger.debug(f"Cache miss for {cache_key}")
            if asyncio.iscoroutinefunction(func):
                value = await func(*args, **kwargs)
            else:
                value = func(*args, **kwargs)

            # Store in cache
            await cache_manager.set_async(cache_key, value, expire)

            return value

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [func.__module__, func.__name__]
            if key_prefix:
                key_parts.insert(0, key_prefix)

            key_data = {"args": args, "kwargs": kwargs}
            key_hash = hashlib.md5(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            cache_key = f"{':'.join(key_parts)}:{key_hash}"

            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Compute value
            logger.debug(f"Cache miss for {cache_key}")
            value = func(*args, **kwargs)

            # Store in cache
            cache_manager.set(cache_key, value, expire)

            return value

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Cache invalidation helpers
def invalidate_user_cache(user_id: str):
    """Invalidate all cache entries for a user"""
    pattern = f"user:{user_id}:*"
    return cache_manager.invalidate_pattern(pattern)


def invalidate_model_cache(model_id: str):
    """Invalidate all cache entries for a model"""
    pattern = f"model:{model_id}:*"
    return cache_manager.invalidate_pattern(pattern)


def invalidate_prediction_cache(prediction_id: str = None):
    """Invalidate prediction cache"""
    if prediction_id:
        pattern = f"prediction:{prediction_id}:*"
    else:
        pattern = "prediction:*"
    return cache_manager.invalidate_pattern(pattern)


# Convenience functions
async def init_cache():
    """Initialize cache manager"""
    await cache_manager.initialize_async()


async def close_cache():
    """Close cache connections"""
    await cache_manager.close_async()


async def check_cache_health() -> bool:
    """Check if cache is healthy"""
    try:
        if not cache_manager.async_redis_client:
            await cache_manager.initialize_async()

        if cache_manager.async_redis_client:
            await cache_manager.async_redis_client.ping()
            return True
        return False
    except:
        return False


def cache_set(key: str, value: Any, expire: int = 3600):
    """Set cache value"""
    return cache_manager.set(key, value, expire)


def cache_get(key: str):
    """Get cache value"""
    return cache_manager.get(key)


def cache_delete(key: str):
    """Delete cache entry"""
    return cache_manager.delete(key)
