#!/usr/bin/env python3
"""
High-performance vector embedding generator for Vector Store Manager
Optimized for 16GB RAM and 2.5GHz octa-core systems
"""

import sys
import json
import os
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time
import gc
from datetime import datetime

# Import high-performance libraries
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import faiss
from sklearn.cluster import KMeans, DBSCAN
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import umap
from scipy.spatial.distance import cosine
import psutil
import joblib

# Document processing
import PyPDF2
from docx import Document
import mammoth
from bs4 import BeautifulSoup
import pandas as pd
import xml.etree.ElementTree as ET
import json as json_lib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("vector_store_manager.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class VectorStoreManager:
    """High-performance vector store manager optimized for resource constraints"""
    
    def __init__(self, vector_store_path: str):
        self.vector_store_path = Path(vector_store_path)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = self.vector_store_path / "vector_store.db"
        self.init_database()
        
        # Model configuration for 16GB RAM
        self.model_name = "all-MiniLM-L6-v2"  # Fast, efficient, 384 dimensions
        self.batch_size = 32  # Optimized for memory constraints
        self.max_length = 512  # Balance between performance and memory
        
        # Initialize embedding model
        self.model = None
        self.tokenizer = None
        self.device = self._get_optimal_device()
        
        # Vector index
        self.index = None
        self.document_embeddings = {}
        
        # Performance monitoring
        self.memory_monitor = MemoryMonitor()
        
    def _get_optimal_device(self) -> str:
        """Determine optimal device based on available resources"""
        if torch.cuda.is_available():
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            if gpu_memory >= 4:  # 4GB+ GPU
                return "cuda"
        return "cpu"
    
    def init_database(self):
        """Initialize SQLite database for document metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                mime_type TEXT,
                upload_date TEXT,
                text_content TEXT,
                embedding_count INTEGER DEFAULT 0,
                processing_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT,
                chunk_index INTEGER,
                text_chunk TEXT,
                embedding_vector BLOB,
                embedding_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vector_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_type TEXT,
                index_data BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_model(self):
        """Load the embedding model with memory optimization"""
        try:
            logger.info(f"Loading model {self.model_name} on {self.device}")
            
            # Use sentence-transformers for better performance
            self.model = SentenceTransformer(self.model_name, device=self.device)
            
            # Optimize model for inference
            if self.device == "cpu":
                self.model.half()  # Use half precision for CPU
            else:
                self.model.eval()  # Set to evaluation mode
            
            logger.info(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def extract_text_from_file(self, file_path: str, mime_type: str) -> str:
        """Extract text content from various file types"""
        try:
            file_path = Path(file_path)
            
            if mime_type == "application/pdf":
                return self._extract_pdf_text(file_path)
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return self._extract_docx_text(file_path)
            elif mime_type == "text/plain":
                return self._extract_txt_text(file_path)
            elif mime_type == "text/markdown":
                return self._extract_md_text(file_path)
            elif mime_type == "text/csv":
                return self._extract_csv_text(file_path)
            elif mime_type == "application/json":
                return self._extract_json_text(file_path)
            elif mime_type == "application/xml" or mime_type == "text/xml":
                return self._extract_xml_text(file_path)
            elif mime_type == "text/html":
                return self._extract_html_text(file_path)
            else:
                # Try to extract as plain text
                return self._extract_txt_text(file_path)
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF files"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
        return text
    
    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX files"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return ""
    
    def _extract_txt_text(self, file_path: Path) -> str:
        """Extract text from plain text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                logger.error(f"Error reading text file: {e}")
                return ""
    
    def _extract_md_text(self, file_path: Path) -> str:
        """Extract text from Markdown files"""
        return self._extract_txt_text(file_path)
    
    def _extract_csv_text(self, file_path: Path) -> str:
        """Extract text from CSV files"""
        try:
            df = pd.read_csv(file_path)
            return df.to_string(index=False)
        except Exception as e:
            logger.error(f"Error extracting CSV text: {e}")
            return self._extract_txt_text(file_path)
    
    def _extract_json_text(self, file_path: Path) -> str:
        """Extract text from JSON files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json_lib.load(file)
                return json_lib.dumps(data, indent=2)
        except Exception as e:
            logger.error(f"Error extracting JSON text: {e}")
            return self._extract_txt_text(file_path)
    
    def _extract_xml_text(self, file_path: Path) -> str:
        """Extract text from XML files"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            return ET.tostring(root, encoding='unicode', method='xml')
        except Exception as e:
            logger.error(f"Error extracting XML text: {e}")
            return self._extract_txt_text(file_path)
    
    def _extract_html_text(self, file_path: Path) -> str:
        """Extract text from HTML files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file.read(), 'html.parser')
                return soup.get_text()
        except Exception as e:
            logger.error(f"Error extracting HTML text: {e}")
            return self._extract_txt_text(file_path)
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better embedding"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def generate_embeddings(self, text_chunks: List[str], document_id: str) -> Dict[str, Any]:
        """Generate embeddings for text chunks with memory optimization"""
        if not self.model:
            self.load_model()
        
        try:
            # Monitor memory usage
            self.memory_monitor.check_memory()
            
            # Generate embeddings in batches
            embeddings = []
            for i in range(0, len(text_chunks), self.batch_size):
                batch = text_chunks[i:i + self.batch_size]
                
                # Generate embeddings
                batch_embeddings = self.model.encode(
                    batch,
                    convert_to_tensor=True,
                    show_progress_bar=False,
                    device=self.device
                )
                
                # Convert to numpy for storage
                if self.device == "cuda":
                    batch_embeddings = batch_embeddings.cpu().numpy()
                else:
                    batch_embeddings = batch_embeddings.numpy()
                
                embeddings.extend(batch_embeddings)
                
                # Clear GPU memory if needed
                if self.device == "cuda":
                    torch.cuda.empty_cache()
                
                # Force garbage collection
                gc.collect()
            
            # Store embeddings in database
            self._store_embeddings(document_id, text_chunks, embeddings)
            
            # Update document status
            self._update_document_status(document_id, "completed", len(embeddings))
            
            return {
                "document_id": document_id,
                "embedding_count": len(embeddings),
                "chunk_count": len(text_chunks),
                "embedding_dimension": embeddings[0].shape[0] if embeddings else 0,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            self._update_document_status(document_id, "failed")
            return {
                "document_id": document_id,
                "status": "failed",
                "error": str(e)
            }
    
    def _store_embeddings(self, document_id: str, text_chunks: List[str], embeddings: List[np.ndarray]):
        """Store embeddings in SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for i, (chunk, embedding) in enumerate(zip(text_chunks, embeddings)):
                # Create hash for embedding
                embedding_hash = hashlib.md5(embedding.tobytes()).hexdigest()
                
                cursor.execute('''
                    INSERT INTO embeddings (document_id, chunk_index, text_chunk, embedding_vector, embedding_hash)
                    VALUES (?, ?, ?, ?, ?)
                ''', (document_id, i, chunk, embedding.tobytes(), embedding_hash))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing embeddings: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _store_document_metadata(self, document_id: str, filename: str, file_path: str, text_content: str, mime_type: str = "application/pdf"):
        """Store document metadata in the documents table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            upload_date = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO documents 
                (id, filename, original_name, file_path, file_size, mime_type, upload_date, text_content, processing_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (document_id, filename, filename, file_path, file_size, mime_type, upload_date, text_content, "processing"))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing document metadata: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _update_document_status(self, document_id: str, status: str, embedding_count: int = 0):
        """Update document processing status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE documents 
                SET processing_status = ?, embedding_count = ?
                WHERE id = ?
            ''', (status, embedding_count, document_id))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating document status: {e}")
        finally:
            conn.close()
    
    def build_vector_index(self):
        """Build FAISS index for fast similarity search"""
        try:
            # Load all embeddings from database
            embeddings = self._load_all_embeddings()
            
            if not embeddings:
                logger.warning("No embeddings found to build index")
                return {"success": False, "error": "No embeddings found"}
            
            # Check minimum embeddings for FAISS
            if len(embeddings) < 10:
                logger.warning(f"Only {len(embeddings)} embeddings found. FAISS requires more embeddings for clustering.")
                return {"success": False, "error": f"Only {len(embeddings)} embeddings found, need at least 10"}
            
            # Convert to numpy array
            embedding_vectors = np.array(embeddings)
            
            # For small datasets, use a simpler index type
            if len(embedding_vectors) < 50:
                # Use FlatL2 index for small datasets (no clustering)
                dimension = embedding_vectors.shape[1]
                self.index = faiss.IndexFlatL2(dimension)
                self.index.add(embedding_vectors)
                
                logger.info(f"Vector index built with {len(embeddings)} embeddings (FlatL2)")
                return {"success": True, "index_type": "FlatL2", "index_size": len(embeddings)}
            else:
                # Use IVFFlat for larger datasets
                dimension = embedding_vectors.shape[1]
                nlist = min(100, max(1, embedding_vectors.shape[0] // 100))  # Number of clusters
                
                # Ensure nlist is at least 1 and not greater than number of vectors
                nlist = max(1, min(nlist, embedding_vectors.shape[0] // 2))
                
                self.index = faiss.IndexIVFFlat(
                    faiss.IndexFlatL2(dimension),  # Quantizer
                    dimension,                      # Dimension
                    nlist,                         # Number of clusters
                    faiss.METRIC_L2               # Distance metric
                )
                
                # Train the index
                self.index.train(embedding_vectors)
                
                # Add vectors to index
                self.index.add(embedding_vectors)
                
                logger.info(f"Vector index built with {len(embeddings)} embeddings (IVFFlat)")
                return {"success": True, "index_type": "IVFFlat", "index_size": len(embeddings)}
            
        except Exception as e:
            logger.error(f"Error building vector index: {e}")
            return {"success": False, "error": str(e)}
    
    def _load_all_embeddings(self) -> List[np.ndarray]:
        """Load all embeddings from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT embedding_vector FROM embeddings ORDER BY id')
            rows = cursor.fetchall()
            
            embeddings = []
            for row in rows:
                embedding_bytes = row[0]
                embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            return []
        finally:
            conn.close()
    
    def search_similar(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        if not self.index:
            index_result = self.build_vector_index()
            if not index_result.get("success"):
                raise RuntimeError(index_result.get("error", "Failed to build vector index"))
        
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query], convert_to_tensor=True)
            if self.device == "cuda":
                query_embedding = query_embedding.cpu().numpy()
            else:
                query_embedding = query_embedding.numpy()
            
            # Search index
            distances, indices = self.index.search(query_embedding, top_k)
            
            # Get document information
            results = []
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                    if idx == -1:  # Invalid index
                        continue
                    
                    cursor.execute('''
                        SELECT e.document_id, e.text_chunk, d.original_name
                        FROM embeddings e
                        JOIN documents d ON e.document_id = d.id
                        ORDER BY e.id
                        LIMIT 1 OFFSET ?
                    ''', (idx,))
                    
                    row = cursor.fetchone()
                    if row:
                        results.append({
                            "rank": i + 1,
                            "document_id": row[0],
                            "document_name": row[2],
                            "text_chunk": row[1],
                            "similarity_score": 1.0 / (1.0 + distance),  # Convert distance to similarity
                            "distance": float(distance)
                        })
            
            finally:
                conn.close()
            
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return []

    def can_perform_semantic_search(self) -> bool:
        """Check if semantic search is available (has enough embeddings)"""
        embeddings = self._load_all_embeddings()
        return len(embeddings) >= 10
    
    def get_semantic_search_status(self) -> Dict[str, Any]:
        """Get detailed status of semantic search availability"""
        embeddings = self._load_all_embeddings()
        return {
            "available": len(embeddings) >= 10,
            "embedding_count": len(embeddings),
            "minimum_required": 10,
            "message": f"Semantic search requires at least 10 embeddings, found {len(embeddings)}"
        }
    
    def search_exact(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for exact text matches in documents"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Search for exact text matches
            cursor.execute('''
                SELECT e.document_id, e.text_chunk, d.original_name, e.chunk_index
                FROM embeddings e
                JOIN documents d ON e.document_id = d.id
                WHERE e.text_chunk LIKE ?
                ORDER BY e.id
                LIMIT ?
            ''', (f'%{query}%', top_k))
            
            rows = cursor.fetchall()
            results = []
            
            for i, row in enumerate(rows):
                results.append({
                    "rank": i + 1,
                    "document_id": row[0],
                    "document_name": row[2],
                    "text_chunk": row[1],
                    "chunk_index": row[3],
                    "similarity_score": 1.0,  # Exact match gets full score
                    "match_type": "exact"
                })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error in exact search: {e}")
            return []


class MemoryMonitor:
    """Monitor and manage memory usage"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.memory_threshold = 0.8  # 80% of available memory
    
    def check_memory(self):
        """Check if memory usage is within acceptable limits"""
        memory_percent = self.process.memory_percent()
        
        if memory_percent > self.memory_threshold * 100:
            logger.warning(f"High memory usage: {memory_percent:.1f}%")
            self._cleanup_memory()
    
    def _cleanup_memory(self):
        """Perform memory cleanup"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 4:
        print("Usage: python generate_embeddings.py <text_content> <document_id> <vector_store_path>")
        sys.exit(1)
    
    text_content = sys.argv[1]
    document_id = sys.argv[2]
    vector_store_path = sys.argv[3]
    
    try:
        # Initialize vector store manager
        manager = VectorStoreManager(vector_store_path)
        
        # Extract text content (assuming it's already extracted)
        if not text_content.strip():
            result = {"status": "error", "message": "Empty text content"}
        else:
            # Chunk text
            text_chunks = manager.chunk_text(text_content)
            
            # Generate embeddings
            result = manager.generate_embeddings(text_chunks, document_id)
        
        # Output result as JSON
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "document_id": document_id
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main() 