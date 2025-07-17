#!/usr/bin/env python3
"""
Vector Store Backend Validation Script

This script validates the vector store backend functionality using the provided PDF.
It tests text extraction, embedding generation, storage, and search capabilities.
"""

import sys
import json
import os
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import time
from datetime import datetime

# Import vector store components
try:
    # Add the myAi/python directory to the path
    myai_python_path = Path(__file__).parent / "myAi" / "python"
    sys.path.insert(0, str(myai_python_path))
    
    from generate_embeddings import VectorStoreManager
    from search_embeddings import VectorSearch
    from extract_text_simple import extract_text_from_file
except ImportError as e:
    print(f"Error: Could not import vector store components: {e}")
    print("Make sure you're running this from the project root directory")
    print(f"Looking for modules in: {myai_python_path}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VectorStoreValidator:
    """Comprehensive validator for vector store backend"""
    
    def __init__(self, test_pdf_path: str, vector_store_path: str = "./test-vector-store"):
        self.test_pdf_path = Path(test_pdf_path)
        self.vector_store_path = Path(vector_store_path)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.vsm = VectorStoreManager(str(self.vector_store_path))
        self.search = VectorSearch(str(self.vector_store_path))
        
        # Test results
        self.results = {
            "test_timestamp": datetime.now().isoformat(),
            "pdf_path": str(self.test_pdf_path),
            "vector_store_path": str(self.vector_store_path),
            "tests": {}
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        logger.info("🚀 Starting Vector Store Backend Validation")
        logger.info(f"📄 Test PDF: {self.test_pdf_path}")
        logger.info(f"🗄️  Vector Store: {self.vector_store_path}")
        
        # Test 1: PDF File Validation
        self._test_pdf_file_validation()
        
        # Test 2: Text Extraction
        self._test_text_extraction()
        
        # Test 3: Vector Store Initialization
        self._test_vector_store_initialization()
        
        # Test 4: Embedding Generation
        self._test_embedding_generation()
        
        # Test 5: Database Storage
        self._test_database_storage()
        
        # Test 6: Vector Index Building
        self._test_vector_index_building()
        
        # Test 7: Search Functionality
        self._test_search_functionality()
        
        # Test 8: Performance Metrics
        self._test_performance_metrics()
        
        # Generate final report
        self._generate_validation_report()
        
        return self.results
    
    def _test_pdf_file_validation(self):
        """Test 1: Validate PDF file exists and is readable"""
        logger.info("📋 Test 1: PDF File Validation")
        
        try:
            if not self.test_pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {self.test_pdf_path}")
            
            file_size = self.test_pdf_path.stat().st_size
            if file_size == 0:
                raise ValueError("PDF file is empty")
            
            self.results["tests"]["pdf_validation"] = {
                "status": "PASS",
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "exists": True,
                "readable": True
            }
            
            logger.info(f"✅ PDF validation passed - Size: {self.results['tests']['pdf_validation']['file_size_mb']} MB")
            
        except Exception as e:
            self.results["tests"]["pdf_validation"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ PDF validation failed: {e}")
    
    def _test_text_extraction(self):
        """Test 2: Extract text from PDF"""
        logger.info("📝 Test 2: Text Extraction")
        
        try:
            # Extract text using the simple extractor
            extracted_text = extract_text_from_file(
                str(self.test_pdf_path), 
                "application/pdf"
            )
            
            if not extracted_text or not extracted_text.strip():
                raise ValueError("No text content extracted from PDF")
            
            # Basic text analysis
            word_count = len(extracted_text.split())
            char_count = len(extracted_text)
            line_count = len(extracted_text.split('\n'))
            
            # Store extracted text for later use
            self.extracted_text = extracted_text
            
            self.results["tests"]["text_extraction"] = {
                "status": "PASS",
                "text_length": char_count,
                "word_count": word_count,
                "line_count": line_count,
                "text_preview": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
            }
            
            logger.info(f"✅ Text extraction passed - {word_count} words, {char_count} characters")
            
        except Exception as e:
            self.results["tests"]["text_extraction"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Text extraction failed: {e}")
    
    def _test_vector_store_initialization(self):
        """Test 3: Initialize vector store"""
        logger.info("🗄️ Test 3: Vector Store Initialization")
        
        try:
            # Check if database was created
            db_path = self.vector_store_path / "vector_store.db"
            if not db_path.exists():
                raise FileNotFoundError("Database file was not created")
            
            # Test database connection and schema
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['documents', 'embeddings', 'vector_index']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                raise ValueError(f"Missing required tables: {missing_tables}")
            
            conn.close()
            
            self.results["tests"]["vector_store_initialization"] = {
                "status": "PASS",
                "database_created": True,
                "tables_found": tables,
                "required_tables_present": True
            }
            
            logger.info(f"✅ Vector store initialization passed - Tables: {tables}")
            
        except Exception as e:
            self.results["tests"]["vector_store_initialization"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Vector store initialization failed: {e}")
    
    def _test_embedding_generation(self):
        """Test 4: Generate embeddings for extracted text"""
        logger.info("🧠 Test 4: Embedding Generation")
        
        try:
            if not hasattr(self, 'extracted_text'):
                raise ValueError("No extracted text available for embedding generation")
            
            # Split text into chunks
            text_chunks = self._split_text_into_chunks(self.extracted_text)
            
            # Generate document ID
            document_id = hashlib.md5(str(self.test_pdf_path).encode()).hexdigest()
            
            # Generate embeddings
            start_time = time.time()
            embedding_result = self.vsm.generate_embeddings(text_chunks, document_id)
            end_time = time.time()
            
            if embedding_result.get("status") != "success":
                raise ValueError(f"Embedding generation failed: {embedding_result.get('error')}")
            
            self.results["tests"]["embedding_generation"] = {
                "status": "PASS",
                "document_id": document_id,
                "chunk_count": len(text_chunks),
                "embedding_count": embedding_result.get("embedding_count", 0),
                "embedding_dimension": embedding_result.get("embedding_dimension", 0),
                "processing_time_seconds": round(end_time - start_time, 2),
                "chunks_preview": text_chunks[:3] if len(text_chunks) > 3 else text_chunks
            }
            
            logger.info(f"✅ Embedding generation passed - {embedding_result.get('embedding_count')} embeddings in {self.results['tests']['embedding_generation']['processing_time_seconds']}s")
            
        except Exception as e:
            self.results["tests"]["embedding_generation"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Embedding generation failed: {e}")
    
    def _test_database_storage(self):
        """Test 5: Verify embeddings are stored in database"""
        logger.info("💾 Test 5: Database Storage")
        
        try:
            db_path = self.vector_store_path / "vector_store.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check documents table
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            
            # Check embeddings table
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            embedding_count = cursor.fetchone()[0]
            
            # Get document details
            cursor.execute("SELECT id, original_name, embedding_count, processing_status FROM documents")
            documents = cursor.fetchall()
            
            conn.close()
            
            if doc_count == 0:
                raise ValueError("No documents found in database")
            
            if embedding_count == 0:
                raise ValueError("No embeddings found in database")
            
            self.results["tests"]["database_storage"] = {
                "status": "PASS",
                "document_count": doc_count,
                "embedding_count": embedding_count,
                "documents": [
                    {
                        "id": doc[0],
                        "name": doc[1],
                        "embedding_count": doc[2],
                        "status": doc[3]
                    } for doc in documents
                ]
            }
            
            logger.info(f"✅ Database storage passed - {doc_count} documents, {embedding_count} embeddings")
            
        except Exception as e:
            self.results["tests"]["database_storage"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Database storage failed: {e}")
    
    def _test_vector_index_building(self):
        """Test 6: Build vector index for search"""
        logger.info("🔍 Test 6: Vector Index Building")
        
        try:
            start_time = time.time()
            self.vsm.build_vector_index()
            end_time = time.time()
            
            # Check if index file was created
            index_path = self.vector_store_path / "faiss_index.bin"
            if not index_path.exists():
                raise FileNotFoundError("FAISS index file was not created")
            
            self.results["tests"]["vector_index_building"] = {
                "status": "PASS",
                "index_created": True,
                "index_file_size_bytes": index_path.stat().st_size,
                "processing_time_seconds": round(end_time - start_time, 2)
            }
            
            logger.info(f"✅ Vector index building passed - Index size: {self.results['tests']['vector_index_building']['index_file_size_bytes']} bytes")
            
        except Exception as e:
            self.results["tests"]["vector_index_building"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Vector index building failed: {e}")
    
    def _test_search_functionality(self):
        """Test 7: Test search functionality"""
        logger.info("🔎 Test 7: Search Functionality")
        
        try:
            # Test queries
            test_queries = [
                "financial statement",
                "revenue",
                "expenses",
                "balance sheet",
                "income statement"
            ]
            
            search_results = {}
            
            for query in test_queries:
                start_time = time.time()
                results = self.vsm.search_similar(query, top_k=3)
                end_time = time.time()
                
                search_results[query] = {
                    "results_count": len(results),
                    "processing_time_seconds": round(end_time - start_time, 3),
                    "top_results": [
                        {
                            "rank": result["rank"],
                            "document_name": result["document_name"],
                            "similarity_score": round(result["similarity_score"], 4),
                            "text_preview": result["text_chunk"][:100] + "..." if len(result["text_chunk"]) > 100 else result["text_chunk"]
                        } for result in results[:2]  # Top 2 results
                    ]
                }
            
            self.results["tests"]["search_functionality"] = {
                "status": "PASS",
                "queries_tested": len(test_queries),
                "search_results": search_results
            }
            
            logger.info(f"✅ Search functionality passed - {len(test_queries)} queries tested")
            
        except Exception as e:
            self.results["tests"]["search_functionality"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Search functionality failed: {e}")
    
    def _test_performance_metrics(self):
        """Test 8: Performance metrics"""
        logger.info("⚡ Test 8: Performance Metrics")
        
        try:
            # Calculate overall performance metrics
            total_tests = len(self.results["tests"])
            passed_tests = sum(1 for test in self.results["tests"].values() if test.get("status") == "PASS")
            failed_tests = total_tests - passed_tests
            
            # Calculate processing times
            processing_times = []
            for test_name, test_result in self.results["tests"].items():
                if "processing_time_seconds" in test_result:
                    processing_times.append(test_result["processing_time_seconds"])
            
            total_processing_time = sum(processing_times)
            
            self.results["tests"]["performance_metrics"] = {
                "status": "PASS" if failed_tests == 0 else "FAIL",
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": round((passed_tests / total_tests) * 100, 1),
                "total_processing_time_seconds": round(total_processing_time, 2),
                "average_processing_time_seconds": round(total_processing_time / len(processing_times), 2) if processing_times else 0
            }
            
            logger.info(f"✅ Performance metrics - {passed_tests}/{total_tests} tests passed ({self.results['tests']['performance_metrics']['success_rate']}%)")
            
        except Exception as e:
            self.results["tests"]["performance_metrics"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Performance metrics failed: {e}")
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for i in range(end, max(start, end - 100), -1):
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
    
    def _generate_validation_report(self):
        """Generate comprehensive validation report"""
        logger.info("📊 Generating Validation Report")
        
        # Calculate overall status
        total_tests = len(self.results["tests"])
        passed_tests = sum(1 for test in self.results["tests"].values() if test.get("status") == "PASS")
        failed_tests = total_tests - passed_tests
        
        self.results["summary"] = {
            "overall_status": "PASS" if failed_tests == 0 else "FAIL",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 1)
        }
        
        # Print summary
        logger.info("=" * 60)
        logger.info("📋 VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Overall Status: {self.results['summary']['overall_status']}")
        logger.info(f"Tests Passed: {passed_tests}/{total_tests} ({self.results['summary']['success_rate']}%)")
        logger.info(f"PDF File: {self.test_pdf_path}")
        logger.info(f"Vector Store: {self.vector_store_path}")
        
        # Print individual test results
        logger.info("\n📝 INDIVIDUAL TEST RESULTS:")
        for test_name, test_result in self.results["tests"].items():
            status_icon = "✅" if test_result.get("status") == "PASS" else "❌"
            logger.info(f"{status_icon} {test_name}: {test_result.get('status')}")
            if test_result.get("error"):
                logger.info(f"   Error: {test_result['error']}")
        
        logger.info("=" * 60)

def main():
    """Main validation function"""
    if len(sys.argv) < 2:
        print("Usage: python validate_vector_store.py <pdf_file_path>")
        print("Example: python validate_vector_store.py mcli/resources/20240131-statements-2119-.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    vector_store_path = sys.argv[2] if len(sys.argv) > 2 else "./test-vector-store"
    
    try:
        # Create validator and run tests
        validator = VectorStoreValidator(pdf_path, vector_store_path)
        results = validator.run_all_tests()
        
        # Save results to file
        results_file = Path(vector_store_path) / "validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        if results["summary"]["overall_status"] == "PASS":
            logger.info("🎉 Vector store backend validation completed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 Vector store backend validation failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Validation script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 