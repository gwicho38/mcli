"""
Cached TF-IDF Vectorizer with Redis support for high-performance text similarity
"""

import asyncio
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Optional redis import - gracefully handle if not installed
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class CachedTfIdfVectorizer:
    """
    TF-IDF Vectorizer with Redis caching for improved performance.
    Falls back to Rust implementation when available, otherwise uses sklearn.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        cache_ttl: int = 3600,
        cache_prefix: str = "tfidf",
        use_rust: bool = True,
    ):
        self.redis_url = redis_url
        self.cache_ttl = cache_ttl
        self.cache_prefix = cache_prefix
        self.use_rust = use_rust

        self.redis_client: Optional[Any] = None  # redis.Redis when available
        self.vectorizer = None
        self.is_fitted = False

        # Cache stats
        self.cache_hits = 0
        self.cache_misses = 0

    async def initialize(self):
        """Initialize Redis connection and vectorizer"""
        await self._init_redis()
        await self._init_vectorizer()

    async def _init_redis(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis is not installed. Caching disabled.")
            self.redis_client = None
            return

        try:
            # Try to ensure Redis is running through the service manager
            try:
                from mcli.lib.services.redis_service import ensure_redis_running

                await ensure_redis_running()
            except ImportError:
                logger.debug("Redis service manager not available")

            self.redis_client = redis.from_url(self.redis_url)  # type: ignore
            await self.redis_client.ping()
            logger.info("Connected to Redis for TF-IDF caching")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.redis_client = None

    async def _init_vectorizer(self):
        """Initialize the appropriate vectorizer implementation"""
        if self.use_rust:
            try:
                # Try to use Rust implementation
                import mcli_rust

                self.vectorizer = mcli_rust.TfIdfVectorizer(
                    max_features=1000, min_df=1, max_df=0.95, ngram_range=(1, 2)
                )
                logger.info("Using Rust TF-IDF vectorizer for enhanced performance")
                return
            except ImportError:
                logger.warning("Rust vectorizer not available, falling back to sklearn")

        # Fallback to sklearn
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self.vectorizer = TfidfVectorizer(
                max_features=1000, stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.95
            )
            logger.info("Using sklearn TF-IDF vectorizer")
        except ImportError:
            raise RuntimeError("Neither Rust nor sklearn TF-IDF implementation available")

    async def fit_transform(self, documents: List[str]) -> np.ndarray:
        """Fit the vectorizer and transform documents with caching"""
        # Generate cache key for the document set
        cache_key = self._generate_cache_key(documents, "fit_transform")

        # Try to get from cache
        cached_result = await self._get_from_cache(cache_key)
        if cached_result is not None:
            self.cache_hits += 1
            vectors, feature_names = cached_result
            self.is_fitted = True
            return vectors

        self.cache_misses += 1

        # Compute TF-IDF vectors
        if hasattr(self.vectorizer, "fit_transform") and hasattr(
            self.vectorizer, "get_feature_names_out"
        ):
            # sklearn implementation
            vectors = self.vectorizer.fit_transform(documents).toarray()
            feature_names = self.vectorizer.get_feature_names_out().tolist()
        else:
            # Rust implementation
            result = self.vectorizer.fit_transform(documents)
            if isinstance(result, list):
                vectors = np.array(result)
            else:
                vectors = result.toarray() if hasattr(result, "toarray") else np.array(result)

            if hasattr(self.vectorizer, "get_feature_names"):
                feature_names = self.vectorizer.get_feature_names()
            else:
                feature_names = [
                    f"feature_{i}"
                    for i in range(vectors.shape[1] if len(vectors.shape) > 1 else len(vectors))
                ]

        self.is_fitted = True

        # Cache the result
        await self._cache_result(cache_key, (vectors, feature_names))

        return vectors

    async def transform(self, documents: List[str]) -> np.ndarray:
        """Transform documents using fitted vectorizer with caching"""
        if not self.is_fitted:
            raise ValueError("Vectorizer must be fitted before transform")

        # Generate cache key for transformation
        cache_key = self._generate_cache_key(documents, "transform")

        # Try to get from cache
        cached_result = await self._get_from_cache(cache_key)
        if cached_result is not None:
            self.cache_hits += 1
            return cached_result

        self.cache_misses += 1

        # Compute vectors
        if hasattr(self.vectorizer, "transform") and hasattr(
            self.vectorizer, "get_feature_names_out"
        ):
            # sklearn implementation
            vectors = self.vectorizer.transform(documents).toarray()
        else:
            # Rust implementation
            result = self.vectorizer.transform(documents)
            if isinstance(result, list):
                vectors = np.array(result)
            else:
                vectors = result.toarray() if hasattr(result, "toarray") else np.array(result)

        # Cache the result
        await self._cache_result(cache_key, vectors)

        return vectors

    async def similarity_search(
        self, query: str, documents: List[str], top_k: int = 10
    ) -> List[Tuple[int, float]]:
        """Perform similarity search with caching"""
        # Generate cache key for similarity search
        search_data = {"query": query, "documents": documents, "top_k": top_k}
        cache_key = self._generate_cache_key_from_dict(search_data, "similarity")

        # Try to get from cache
        cached_result = await self._get_from_cache(cache_key)
        if cached_result is not None:
            self.cache_hits += 1
            return cached_result

        self.cache_misses += 1

        # Compute similarity
        if hasattr(self.vectorizer, "similarity"):
            # Rust implementation with built-in similarity
            similarities = self.vectorizer.similarity(query, documents)
        else:
            # sklearn implementation - need to compute manually
            if not self.is_fitted:
                await self.fit_transform(documents)

            query_vector = await self.transform([query])
            doc_vectors = await self.transform(documents)

            # Compute cosine similarity
            similarities = []
            for doc_vector in doc_vectors:
                similarity = self._cosine_similarity(query_vector[0], doc_vector)
                similarities.append(similarity)

        # Get top-k results
        indexed_similarities = [(i, sim) for i, sim in enumerate(similarities)]
        indexed_similarities.sort(key=lambda x: x[1], reverse=True)
        results = indexed_similarities[:top_k]

        # Cache the result
        await self._cache_result(cache_key, results)

        return results

    async def batch_similarity_search(
        self, queries: List[str], documents: List[str], top_k: int = 10
    ) -> List[List[Tuple[int, float]]]:
        """Perform batch similarity search for multiple queries"""
        # Try to use cached individual results first
        results = []
        uncached_queries = []
        uncached_indices = []

        for i, query in enumerate(queries):
            cache_key = self._generate_cache_key_from_dict(
                {"query": query, "documents": documents, "top_k": top_k}, "similarity"
            )

            cached_result = await self._get_from_cache(cache_key)
            if cached_result is not None:
                self.cache_hits += 1
                results.append(cached_result)
            else:
                self.cache_misses += 1
                results.append(None)
                uncached_queries.append(query)
                uncached_indices.append(i)

        # Process uncached queries in batch
        if uncached_queries:
            if hasattr(self.vectorizer, "similarity"):
                # Rust implementation might support batch processing
                for j, query in enumerate(uncached_queries):
                    similarities = self.vectorizer.similarity(query, documents)
                    indexed_similarities = [(i, sim) for i, sim in enumerate(similarities)]
                    indexed_similarities.sort(key=lambda x: x[1], reverse=True)
                    query_results = indexed_similarities[:top_k]

                    # Update results and cache
                    results[uncached_indices[j]] = query_results
                    cache_key = self._generate_cache_key_from_dict(
                        {"query": query, "documents": documents, "top_k": top_k}, "similarity"
                    )
                    await self._cache_result(cache_key, query_results)
            else:
                # sklearn implementation
                if not self.is_fitted:
                    await self.fit_transform(documents)

                query_vectors = await self.transform(uncached_queries)
                doc_vectors = await self.transform(documents)

                for j, query_vector in enumerate(query_vectors):
                    similarities = []
                    for doc_vector in doc_vectors:
                        similarity = self._cosine_similarity(query_vector, doc_vector)
                        similarities.append(similarity)

                    indexed_similarities = [(i, sim) for i, sim in enumerate(similarities)]
                    indexed_similarities.sort(key=lambda x: x[1], reverse=True)
                    query_results = indexed_similarities[:top_k]

                    # Update results and cache
                    results[uncached_indices[j]] = query_results
                    cache_key = self._generate_cache_key_from_dict(
                        {"query": uncached_queries[j], "documents": documents, "top_k": top_k},
                        "similarity",
                    )
                    await self._cache_result(cache_key, query_results)

        return results

    def _generate_cache_key(self, documents: List[str], operation: str) -> str:
        """Generate a cache key for a list of documents and operation"""
        content = f"{operation}:{':'.join(documents)}"
        hash_obj = hashlib.sha256(content.encode("utf-8"))
        return f"{self.cache_prefix}:{hash_obj.hexdigest()[:16]}"

    def _generate_cache_key_from_dict(self, data: Dict[str, Any], operation: str) -> str:
        """Generate a cache key from a dictionary"""
        content = f"{operation}:{json.dumps(data, sort_keys=True)}"
        hash_obj = hashlib.sha256(content.encode("utf-8"))
        return f"{self.cache_prefix}:{hash_obj.hexdigest()[:16]}"

    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from Redis cache"""
        if not self.redis_client:
            return None

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return pickle.loads(cached_data)
        except Exception as e:
            logger.warning(f"Failed to get from cache: {e}")

        return None

    async def _cache_result(self, cache_key: str, result: Any):
        """Cache result in Redis"""
        if not self.redis_client:
            return

        try:
            serialized_result = pickle.dumps(result)
            await self.redis_client.setex(cache_key, self.cache_ttl, serialized_result)
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache entries"""
        if not self.redis_client:
            return

        try:
            if pattern:
                keys = await self.redis_client.keys(f"{self.cache_prefix}:{pattern}")
            else:
                keys = await self.redis_client.keys(f"{self.cache_prefix}:*")

            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0
                else 0.0
            ),
            "redis_connected": self.redis_client is not None,
            "vectorizer_type": (
                "rust" if self.use_rust and "mcli_rust" in str(type(self.vectorizer)) else "sklearn"
            ),
        }

        if self.redis_client:
            try:
                # Get Redis memory usage
                info = await self.redis_client.info("memory")
                stats["redis_memory_used"] = info.get("used_memory_human", "unknown")

                # Count cache entries
                keys = await self.redis_client.keys(f"{self.cache_prefix}:*")
                stats["cached_entries"] = len(keys)
            except Exception as e:
                logger.warning(f"Failed to get Redis stats: {e}")

        return stats

    async def warm_cache(self, documents: List[str], common_queries: List[str]):
        """Pre-populate cache with common queries"""
        logger.info(
            f"Warming cache with {len(common_queries)} queries and {len(documents)} documents"
        )

        # Fit the vectorizer if not already fitted
        if not self.is_fitted:
            await self.fit_transform(documents)

        # Pre-compute similarities for common queries
        for i, query in enumerate(common_queries):
            await self.similarity_search(query, documents)
            if i % 10 == 0:
                logger.info(f"Warmed {i + 1}/{len(common_queries)} queries")

        logger.info("Cache warming completed")

    async def close(self):
        """Clean up resources"""
        if self.redis_client:
            await self.redis_client.close()

        # Print final stats
        stats = await self.get_cache_stats()
        logger.info(f"TF-IDF Cache Stats: {stats}")


class SmartVectorizerManager:
    """
    Manager for multiple cached vectorizers with automatic model selection
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.vectorizers: Dict[str, CachedTfIdfVectorizer] = {}
        self.default_vectorizer = None

    async def get_vectorizer(
        self,
        domain: str = "default",
        max_features: int = 1000,
        ngram_range: Tuple[int, int] = (1, 2),
    ) -> CachedTfIdfVectorizer:
        """Get or create a vectorizer for a specific domain"""
        vectorizer_key = f"{domain}_{max_features}_{ngram_range[0]}_{ngram_range[1]}"

        if vectorizer_key not in self.vectorizers:
            vectorizer = CachedTfIdfVectorizer(
                redis_url=self.redis_url, cache_prefix=f"tfidf_{domain}", use_rust=True
            )
            await vectorizer.initialize()
            self.vectorizers[vectorizer_key] = vectorizer

            if self.default_vectorizer is None:
                self.default_vectorizer = vectorizer

        return self.vectorizers[vectorizer_key]

    async def search_commands(
        self, query: str, commands: List[Dict[str, Any]], top_k: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Search commands using optimized vectorization"""
        vectorizer = await self.get_vectorizer("commands")

        # Extract searchable text from commands
        documents = []
        for cmd in commands:
            text_parts = [
                cmd.get("name", ""),
                cmd.get("description", ""),
                " ".join(cmd.get("tags", [])),
            ]
            documents.append(" ".join(filter(None, text_parts)))

        # Perform similarity search
        results = await vectorizer.similarity_search(query, documents, top_k)

        # Return commands with their similarity scores
        return [(commands[idx], score) for idx, score in results]

    async def close_all(self):
        """Close all vectorizers"""
        for vectorizer in self.vectorizers.values():
            await vectorizer.close()
        self.vectorizers.clear()
