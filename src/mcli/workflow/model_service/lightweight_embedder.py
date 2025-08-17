#!/usr/bin/env python3
"""
Lightweight Text Embedder for MCLI Model Service

This module provides lightweight text embedding capabilities
that don't require heavy ML libraries like PyTorch or transformers.
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

# Try to import lightweight alternatives
try:
    import sentence_transformers

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import sklearn
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)


class LightweightEmbedder:
    """Lightweight text embedder with multiple fallback methods"""

    def __init__(self, models_dir: str = "./models/embeddings"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.vectorizer = None
        self.embedding_cache = {}

    def get_embedding_method(self) -> str:
        """Determine the best available embedding method"""
        if HAS_SENTENCE_TRANSFORMERS:
            return "sentence_transformers"
        elif HAS_SKLEARN:
            return "tfidf"
        else:
            return "simple_hash"

    def embed_text(self, text: str, method: Optional[str] = None) -> Dict[str, Any]:
        """Embed text using the specified or best available method"""
        if not method:
            method = self.get_embedding_method()

        try:
            if method == "sentence_transformers":
                return self._embed_with_sentence_transformers(text)
            elif method == "tfidf":
                return self._embed_with_tfidf(text)
            else:
                return self._embed_with_simple_hash(text)
        except Exception as e:
            logger.error(f"Error embedding text with {method}: {e}")
            # Fallback to simple hash
            return self._embed_with_simple_hash(text)

    def _embed_with_sentence_transformers(self, text: str) -> Dict[str, Any]:
        """Embed text using sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer

            # Use a lightweight model
            model_name = "all-MiniLM-L6-v2"
            model = SentenceTransformer(model_name)

            # Generate embedding
            embedding = model.encode(text)

            return {
                "method": "sentence_transformers",
                "model": model_name,
                "embedding": embedding.tolist(),
                "dimensions": len(embedding),
                "text_length": len(text),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Sentence transformers embedding failed: {e}")
            raise

    def _embed_with_tfidf(self, text: str) -> Dict[str, Any]:
        """Embed text using TF-IDF"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            # Create or reuse vectorizer
            if self.vectorizer is None:
                self.vectorizer = TfidfVectorizer(
                    max_features=1000, stop_words="english", ngram_range=(1, 2)
                )
                # Fit on the current text
                self.vectorizer.fit([text])

            # Transform text to TF-IDF vector
            tfidf_vector = self.vectorizer.transform([text])
            embedding = tfidf_vector.toarray()[0]

            return {
                "method": "tfidf",
                "model": "sklearn_tfidf",
                "embedding": embedding.tolist(),
                "dimensions": len(embedding),
                "text_length": len(text),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"TF-IDF embedding failed: {e}")
            raise

    def _embed_with_simple_hash(self, text: str) -> Dict[str, Any]:
        """Embed text using simple hash-based method"""
        try:
            # Create a simple hash-based embedding
            words = text.lower().split()
            word_freq = {}

            # Count word frequencies
            for word in words:
                if len(word) > 2:  # Skip very short words
                    word_freq[word] = word_freq.get(word, 0) + 1

            # Create a fixed-size embedding using hashes
            embedding_size = 128
            embedding = np.zeros(embedding_size)

            for word, freq in word_freq.items():
                # Create hash of word
                word_hash = hash(word) % embedding_size
                embedding[word_hash] += freq

            # Normalize the embedding
            if np.sum(embedding) > 0:
                embedding = embedding / np.sum(embedding)

            return {
                "method": "simple_hash",
                "model": "hash_based",
                "embedding": embedding.tolist(),
                "dimensions": len(embedding),
                "text_length": len(text),
                "word_count": len(words),
                "unique_words": len(word_freq),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Simple hash embedding failed: {e}")
            raise

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap

            if start >= len(text):
                break

        return chunks

    def embed_document(self, text: str, chunk_size: int = 1000) -> Dict[str, Any]:
        """Embed a document by chunking and embedding each chunk"""
        try:
            # Split text into chunks
            chunks = self.chunk_text(text, chunk_size)

            # Embed each chunk
            chunk_embeddings = []
            for i, chunk in enumerate(chunks):
                embedding_result = self.embed_text(chunk)
                chunk_embeddings.append(
                    {
                        "chunk_index": i,
                        "chunk_text": chunk[:100] + "..." if len(chunk) > 100 else chunk,
                        "embedding": embedding_result,
                    }
                )

            # Create document-level summary
            total_chunks = len(chunk_embeddings)
            total_text_length = len(text)

            return {
                "success": True,
                "document_embedding": {
                    "total_chunks": total_chunks,
                    "total_text_length": total_text_length,
                    "chunk_embeddings": chunk_embeddings,
                    "method": (
                        chunk_embeddings[0]["embedding"]["method"]
                        if chunk_embeddings
                        else "unknown"
                    ),
                    "timestamp": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error embedding document: {e}")
            return {"success": False, "error": str(e)}

    def search_similar(self, query: str, embeddings: List[Dict], top_k: int = 5) -> List[Dict]:
        """Search for similar documents using embeddings"""
        try:
            # Embed the query
            query_embedding = self.embed_text(query)
            query_vector = np.array(query_embedding["embedding"])

            results = []

            for doc_embedding in embeddings:
                # Calculate similarity for each chunk
                similarities = []
                for chunk in doc_embedding.get("chunk_embeddings", []):
                    chunk_vector = np.array(chunk["embedding"]["embedding"])

                    # Calculate cosine similarity
                    similarity = np.dot(query_vector, chunk_vector) / (
                        np.linalg.norm(query_vector) * np.linalg.norm(chunk_vector)
                    )
                    similarities.append(similarity)

                # Use the best similarity score
                best_similarity = max(similarities) if similarities else 0

                results.append(
                    {
                        "document_id": doc_embedding.get("document_id"),
                        "similarity": float(best_similarity),
                        "chunk_count": len(doc_embedding.get("chunk_embeddings", [])),
                        "text_length": doc_embedding.get("total_text_length", 0),
                    }
                )

            # Sort by similarity and return top_k
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            return []

    def get_status(self) -> Dict[str, Any]:
        """Get the status of the embedder"""
        return {
            "available_methods": {
                "sentence_transformers": HAS_SENTENCE_TRANSFORMERS,
                "tfidf": HAS_SKLEARN,
                "simple_hash": True,  # Always available
            },
            "current_method": self.get_embedding_method(),
            "models_dir": str(self.models_dir),
            "cache_size": len(self.embedding_cache),
        }


def create_embedder_api():
    """Create a simple API for the embedder"""
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class EmbedderHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, embedder=None, **kwargs):
            self.embedder = embedder
            super().__init__(*args, **kwargs)

        def do_POST(self):
            """Handle embedding requests"""
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            if path == "/embed-text":
                self._handle_embed_text()
            elif path == "/embed-document":
                self._handle_embed_document()
            elif path == "/search":
                self._handle_search()
            else:
                self._send_response(404, {"error": "Endpoint not found"})

        def do_GET(self):
            """Handle status requests"""
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            if path == "/status":
                status = self.embedder.get_status()
                self._send_response(200, status)
            else:
                self._send_response(404, {"error": "Endpoint not found"})

        def _handle_embed_text(self):
            """Handle text embedding requests"""
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode("utf-8"))

                text = request_data.get("text")
                method = request_data.get("method")

                if not text:
                    self._send_response(400, {"error": "Text is required"})
                    return

                result = self.embedder.embed_text(text, method)
                self._send_response(200, result)

            except Exception as e:
                self._send_response(500, {"error": str(e)})

        def _handle_embed_document(self):
            """Handle document embedding requests"""
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode("utf-8"))

                text = request_data.get("text")
                chunk_size = request_data.get("chunk_size", 1000)

                if not text:
                    self._send_response(400, {"error": "Text is required"})
                    return

                result = self.embedder.embed_document(text, chunk_size)
                self._send_response(200, result)

            except Exception as e:
                self._send_response(500, {"error": str(e)})

        def _handle_search(self):
            """Handle search requests"""
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode("utf-8"))

                query = request_data.get("query")
                embeddings = request_data.get("embeddings", [])
                top_k = request_data.get("top_k", 5)

                if not query:
                    self._send_response(400, {"error": "Query is required"})
                    return

                results = self.embedder.search_similar(query, embeddings, top_k)
                self._send_response(200, {"results": results})

            except Exception as e:
                self._send_response(500, {"error": str(e)})

        def _send_response(self, status_code, data):
            """Send JSON response"""
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

    return EmbedderHandler


if __name__ == "__main__":
    # Test the embedder
    embedder = LightweightEmbedder()

    # Test with sample text
    test_text = "This is a sample text for testing the lightweight embedder."
    result = embedder.embed_text(test_text)
    print(json.dumps(result, indent=2))

    # Test document embedding
    doc_result = embedder.embed_document(test_text * 10)  # Longer text
    print(json.dumps(doc_result, indent=2))
