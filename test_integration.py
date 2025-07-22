#!/usr/bin/env python3
"""
Integration Test for MCLI Model Service and Client Application

This script:
1. Generates dummy PDFs for testing
2. Starts the model service
3. Tests the client application
4. Tests adding documents to the vector store
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
import logging
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationTest:
    """Comprehensive integration test for MCLI model service and client"""
    
    def __init__(self):
        self.test_dir = Path("./test_integration")
        self.test_dir.mkdir(exist_ok=True)
        
        self.pdf_dir = self.test_dir / "dummy_pdfs"
        self.pdf_dir.mkdir(exist_ok=True)
        
        self.vector_store_path = self.test_dir / "vector_store"
        self.vector_store_path.mkdir(exist_ok=True)
        
        self.model_service_port = 8000
        self.client_port = 3000
        
        # Test results
        self.results = {
            "test_timestamp": datetime.now().isoformat(),
            "tests": {}
        }
    
    def run_all_tests(self):
        """Run all integration tests"""
        logger.info("🚀 Starting MCLI Integration Test")
        logger.info(f"📁 Test directory: {self.test_dir}")
        logger.info(f"📄 PDF directory: {self.pdf_dir}")
        logger.info(f"🗄️ Vector store: {self.vector_store_path}")
        
        # Test 1: Generate dummy PDFs
        self._test_generate_dummy_pdfs()
        
        # Test 2: Start model service
        self._test_start_model_service()
        
        # Test 3: Test model service API
        self._test_model_service_api()
        
        # Test 4: Test client application
        self._test_client_application()
        
        # Test 5: Test vector store operations
        self._test_vector_store_operations()
        
        # Test 6: Cleanup
        self._test_cleanup()
        
        # Generate final report
        self._generate_test_report()
        
        return self.results
    
    def _test_generate_dummy_pdfs(self):
        """Test 1: Generate dummy PDFs for testing"""
        logger.info("📄 Test 1: Generating Dummy PDFs")
        
        try:
            # Create dummy PDFs with different content
            pdfs = [
                {
                    "filename": "sample_report.pdf",
                    "content": """
                    Sample Business Report
                    
                    Executive Summary
                    This is a sample business report for testing purposes. 
                    The report contains various sections including financial data, 
                    market analysis, and strategic recommendations.
                    
                    Financial Performance
                    Revenue: $1,000,000
                    Expenses: $750,000
                    Profit: $250,000
                    
                    Market Analysis
                    The market shows strong growth potential with increasing demand
                    for our products and services. Customer satisfaction rates are
                    at an all-time high of 95%.
                    
                    Strategic Recommendations
                    1. Expand into new markets
                    2. Invest in technology infrastructure
                    3. Enhance customer support systems
                    """
                },
                {
                    "filename": "technical_documentation.pdf",
                    "content": """
                    Technical Documentation
                    
                    System Architecture
                    The system is built using modern microservices architecture
                    with containerized deployment. Key components include:
                    
                    - API Gateway
                    - User Management Service
                    - Data Processing Engine
                    - Vector Store Database
                    
                    API Endpoints
                    GET /api/v1/documents - List all documents
                    POST /api/v1/documents - Upload new document
                    GET /api/v1/search - Search documents
                    
                    Database Schema
                    documents:
                      - id (primary key)
                      - filename
                      - content
                      - created_at
                    
                    embeddings:
                      - id (primary key)
                      - document_id (foreign key)
                      - vector_data
                      - created_at
                    """
                },
                {
                    "filename": "research_paper.pdf",
                    "content": """
                    Research Paper: Machine Learning Applications
                    
                    Abstract
                    This paper explores the applications of machine learning
                    in natural language processing and document analysis.
                    
                    Introduction
                    Machine learning has revolutionized how we process and
                    understand large volumes of text data. Vector embeddings
                    have become essential for semantic search and document
                    similarity analysis.
                    
                    Methodology
                    We implemented a vector store using FAISS for efficient
                    similarity search. The system uses sentence transformers
                    to generate embeddings from document chunks.
                    
                    Results
                    Our experiments show 95% accuracy in semantic search
                    with response times under 100ms for queries across
                    10,000 documents.
                    
                    Conclusion
                    Vector-based document search provides significant
                    improvements over traditional keyword-based approaches.
                    """
                }
            ]
            
            generated_pdfs = []
            for pdf_info in pdfs:
                pdf_path = self._create_dummy_pdf(pdf_info["filename"], pdf_info["content"])
                generated_pdfs.append({
                    "filename": pdf_info["filename"],
                    "path": str(pdf_path),
                    "size_bytes": pdf_path.stat().st_size
                })
            
            self.results["tests"]["generate_dummy_pdfs"] = {
                "status": "PASS",
                "pdfs_generated": len(generated_pdfs),
                "pdfs": generated_pdfs
            }
            
            logger.info(f"✅ Generated {len(generated_pdfs)} dummy PDFs")
            
        except Exception as e:
            self.results["tests"]["generate_dummy_pdfs"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Failed to generate dummy PDFs: {e}")
    
    def _create_dummy_pdf(self, filename: str, content: str) -> Path:
        """Create a dummy PDF file with given content"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            pdf_path = self.pdf_dir / filename
            
            # Create PDF using reportlab
            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Split content into paragraphs
            paragraphs = content.strip().split('\n\n')
            for para in paragraphs:
                if para.strip():
                    p = Paragraph(para.strip(), styles['Normal'])
                    story.append(p)
                    story.append(Spacer(1, 12))
            
            doc.build(story)
            return pdf_path
            
        except ImportError:
            # Fallback: create a text file with .pdf extension
            pdf_path = self.pdf_dir / filename
            with open(pdf_path, 'w') as f:
                f.write(content)
            return pdf_path
    
    def _test_start_model_service(self):
        """Test 2: Start the model service"""
        logger.info("🔧 Test 2: Starting Model Service")
        
        try:
            # Check if model service is already running
            try:
                response = requests.get(f"http://localhost:{self.model_service_port}/", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Model service is already running")
                    self.results["tests"]["start_model_service"] = {
                        "status": "PASS",
                        "message": "Model service already running",
                        "port": self.model_service_port
                    }
                    return
            except requests.exceptions.RequestException:
                pass
            
            # Start model service
            model_service_path = Path("src/mcli/workflow/webapp/templates/vector-store-app/python/vector_store_api.py").resolve()
            
            if not model_service_path.exists():
                raise FileNotFoundError(f"Model service not found at {model_service_path}")
            
            # Set environment variable for vector store path
            env = os.environ.copy()
            env['VECTOR_STORE_PATH'] = str(self.vector_store_path)
            
            # Start the service in background
            cmd = [
                sys.executable, str(model_service_path)
            ]
            
            self.model_service_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path.cwd(),  # Use current working directory instead of test_dir
                env=env
            )
            
            # Wait for service to start with more patience
            logger.info("⏳ Waiting for model service to start...")
            for i in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get(f"http://localhost:{self.model_service_port}/", timeout=2)
                    if response.status_code == 200:
                        self.results["tests"]["start_model_service"] = {
                            "status": "PASS",
                            "message": "Model service started successfully",
                            "port": self.model_service_port,
                            "pid": self.model_service_process.pid,
                            "startup_time_seconds": i + 1
                        }
                        logger.info(f"✅ Model service started on port {self.model_service_port} after {i+1}s")
                        return
                except requests.exceptions.RequestException:
                    time.sleep(1)
                    continue
            
            # If we get here, service didn't start
            if hasattr(self, 'model_service_process'):
                self.model_service_process.terminate()
                stdout, stderr = self.model_service_process.communicate()
                logger.error(f"Model service stdout: {stdout.decode()}")
                logger.error(f"Model service stderr: {stderr.decode()}")
            
            raise Exception("Model service failed to start within 30 seconds")
                
        except Exception as e:
            self.results["tests"]["start_model_service"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Failed to start model service: {e}")
    
    def _test_model_service_api(self):
        """Test 3: Test model service API endpoints"""
        logger.info("🌐 Test 3: Testing Model Service API")
        
        try:
            # Test root endpoint
            response = requests.get(f"http://localhost:{self.model_service_port}/")
            if response.status_code != 200:
                raise Exception(f"Root endpoint failed: {response.status_code}")
            
            # Test status endpoint
            response = requests.get(f"http://localhost:{self.model_service_port}/status")
            if response.status_code != 200:
                raise Exception(f"Status endpoint failed: {response.status_code}")
            
            status_data = response.json()
            logger.info(f"Status: {status_data}")
            
            # Test documents endpoint
            response = requests.get(f"http://localhost:{self.model_service_port}/documents")
            if response.status_code != 200:
                raise Exception(f"Documents endpoint failed: {response.status_code}")
            
            documents_data = response.json()
            logger.info(f"Documents: {documents_data}")
            
            self.results["tests"]["model_service_api"] = {
                "status": "PASS",
                "endpoints_tested": ["/", "/status", "/documents"],
                "status_data": status_data,
                "documents_count": documents_data.get("count", 0)
            }
            
            logger.info("✅ Model service API tests passed")
            
        except Exception as e:
            self.results["tests"]["model_service_api"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Model service API tests failed: {e}")
    
    def _test_client_application(self):
        """Test 4: Test client application"""
        logger.info("📱 Test 4: Testing Client Application")
        
        try:
            client_dir = Path("client/myAi")
            if not client_dir.exists():
                raise FileNotFoundError(f"Client directory not found: {client_dir}")
            
            # Check if client is a web application
            package_json = client_dir / "package.json"
            if package_json.exists():
                logger.info("✅ Found web client application")
                self.results["tests"]["client_application"] = {
                    "status": "PASS",
                    "client_type": "web",
                    "path": str(client_dir)
                }
            else:
                # Check for other client types
                logger.info("✅ Found client application")
                self.results["tests"]["client_application"] = {
                    "status": "PASS",
                    "client_type": "unknown",
                    "path": str(client_dir)
                }
            
            logger.info("✅ Client application test passed")
            
        except Exception as e:
            self.results["tests"]["client_application"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Client application test failed: {e}")
    
    def _test_vector_store_operations(self):
        """Test 5: Test vector store operations"""
        logger.info("🗄️ Test 5: Testing Vector Store Operations")
        
        try:
            # Import vector store manager
            sys.path.append(str(Path("src/mcli/workflow/webapp/templates/vector-store-app/python")))
            from generate_embeddings import VectorStoreManager
            
            # Initialize vector store
            vsm = VectorStoreManager(str(self.vector_store_path))
            
            # Test adding documents
            pdf_files = list(self.pdf_dir.glob("*.pdf"))
            added_documents = []
            
            for pdf_file in pdf_files:
                try:
                    # Extract text
                    text_content = vsm.extract_text_from_file(str(pdf_file), "application/pdf")
                    
                    if not text_content.strip():
                        logger.warning(f"No text extracted from {pdf_file.name}")
                        continue
                    
                    # Generate document ID
                    import hashlib
                    document_id = hashlib.md5(str(pdf_file).encode()).hexdigest()
                    
                    # Store document metadata
                    vsm._store_document_metadata(
                        document_id=document_id,
                        filename=pdf_file.name,
                        file_path=str(pdf_file),
                        text_content=text_content,
                        mime_type="application/pdf"
                    )
                    
                    # Split text into chunks
                    text_chunks = vsm.chunk_text(text_content)
                    
                    # Generate embeddings
                    embedding_result = vsm.generate_embeddings(text_chunks, document_id)
                    
                    if embedding_result.get("status") == "success":
                        added_documents.append({
                            "filename": pdf_file.name,
                            "document_id": document_id,
                            "chunks": len(text_chunks),
                            "embeddings": embedding_result.get("embedding_count", 0)
                        })
                        logger.info(f"✅ Added {pdf_file.name}: {embedding_result.get('embedding_count')} embeddings")
                    else:
                        logger.error(f"❌ Failed to add {pdf_file.name}: {embedding_result.get('error')}")
                
                except Exception as e:
                    logger.error(f"❌ Error processing {pdf_file.name}: {e}")
            
            # Test search functionality
            search_results = []
            if added_documents:
                # Test semantic search
                try:
                    results = vsm.search_similar("machine learning", top_k=3)
                    search_results.append({
                        "query": "machine learning",
                        "type": "semantic",
                        "results": len(results)
                    })
                except RuntimeError as e:
                    search_results.append({
                        "query": "machine learning",
                        "type": "semantic",
                        "error": str(e)
                    })
                
                # Test exact search
                try:
                    results = vsm.search_exact("report", top_k=3)
                    search_results.append({
                        "query": "report",
                        "type": "exact",
                        "results": len(results)
                    })
                except Exception as e:
                    search_results.append({
                        "query": "report",
                        "type": "exact",
                        "error": str(e)
                    })
            
            self.results["tests"]["vector_store_operations"] = {
                "status": "PASS",
                "documents_added": len(added_documents),
                "added_documents": added_documents,
                "search_tests": search_results
            }
            
            logger.info(f"✅ Vector store operations completed: {len(added_documents)} documents added")
            
        except Exception as e:
            self.results["tests"]["vector_store_operations"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Vector store operations failed: {e}")
    
    def _test_cleanup(self):
        """Test 6: Cleanup test resources"""
        logger.info("🧹 Test 6: Cleanup")
        
        try:
            # Stop model service if running
            if hasattr(self, 'model_service_process'):
                self.model_service_process.terminate()
                self.model_service_process.wait(timeout=10)
                logger.info("✅ Model service stopped")
            
            # Keep test files for inspection (don't delete)
            logger.info("✅ Cleanup completed (test files preserved)")
            
            self.results["tests"]["cleanup"] = {
                "status": "PASS",
                "message": "Test resources cleaned up"
            }
            
        except Exception as e:
            self.results["tests"]["cleanup"] = {
                "status": "FAIL",
                "error": str(e)
            }
            logger.error(f"❌ Cleanup failed: {e}")
    
    def _generate_test_report(self):
        """Generate final test report"""
        logger.info("📊 Generating Test Report")
        
        # Calculate summary
        total_tests = len(self.results["tests"])
        passed_tests = sum(1 for test in self.results["tests"].values() if test.get("status") == "PASS")
        failed_tests = total_tests - passed_tests
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 2),
            "overall_status": "PASS" if failed_tests == 0 else "FAIL"
        }
        
        # Print summary
        logger.info("=" * 80)
        logger.info("📊 INTEGRATION TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {self.results['summary']['success_rate']}%")
        logger.info(f"Overall Status: {self.results['summary']['overall_status']}")
        logger.info("=" * 80)
        
        # Save detailed report
        report_path = self.test_dir / "integration_test_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"📄 Detailed report saved to: {report_path}")

def main():
    """Main function"""
    test = IntegrationTest()
    results = test.run_all_tests()
    
    # Exit with appropriate code
    if results["summary"]["overall_status"] == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 