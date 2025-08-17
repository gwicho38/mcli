#!/usr/bin/env python3
"""
PDF Processor for Lightweight Model Service

This module provides PDF text extraction and processing capabilities
that integrate with the lightweight model service for AI-powered
document analysis.
"""

import base64
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# PDF processing libraries
try:
    import fitz  # PyMuPDF
    import PyPDF2
except ImportError:
    print("Warning: PDF libraries not available. Install with: pip install PyPDF2 PyMuPDF")

# Import lightweight model server
from .lightweight_model_server import LIGHTWEIGHT_MODELS, LightweightModelServer

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF processing with lightweight model integration"""

    def __init__(self, models_dir: str = "./models/lightweight", port: int = 8080):
        self.models_dir = Path(models_dir)
        self.port = port
        self.lightweight_server = LightweightModelServer(models_dir, port)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pdf_processor_"))

    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text from PDF with enhanced processing"""
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                return {"error": f"PDF file not found: {pdf_path}"}

            # Extract text using multiple methods for better results
            text_content = self._extract_pdf_text_enhanced(pdf_path)

            if not text_content.strip():
                return {"error": "No text content extracted from PDF"}

            return {
                "success": True,
                "text": text_content,
                "text_length": len(text_content),
                "file_path": str(pdf_path),
                "extraction_method": "enhanced",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return {"error": str(e)}

    def _extract_pdf_text_enhanced(self, pdf_path: Path) -> str:
        """Enhanced PDF text extraction using multiple methods"""
        text_content = ""

        try:
            # Method 1: PyMuPDF (fitz) - better text extraction
            if "fitz" in globals():
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text_content += page.get_text() + "\n"
                doc.close()
                logger.info(f"Extracted {len(text_content)} characters using PyMuPDF")
                return text_content
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")

        try:
            # Method 2: PyPDF2 - fallback
            if "PyPDF2" in globals():
                with open(pdf_path, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text_content += page.extract_text() + "\n"
                logger.info(f"Extracted {len(text_content)} characters using PyPDF2")
                return text_content
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")

        return text_content

    def process_pdf_with_ai(self, pdf_path: str, model_key: Optional[str] = None) -> Dict[str, Any]:
        """Process PDF with AI model for enhanced analysis"""
        try:
            # Extract text first
            extraction_result = self.extract_text_from_pdf(pdf_path)
            if not extraction_result.get("success"):
                return extraction_result

            text_content = extraction_result["text"]

            # Auto-select model if not specified
            if not model_key:
                model_key = self.lightweight_server.recommend_model()

            # Ensure model is downloaded and loaded
            if model_key not in self.lightweight_server.loaded_models:
                success = self.lightweight_server.download_and_load_model(model_key)
                if not success:
                    return {"error": f"Failed to load model: {model_key}"}

            # Process text with AI model
            ai_analysis = self._analyze_text_with_ai(text_content, model_key)

            return {
                "success": True,
                "pdf_analysis": {
                    "text_extraction": extraction_result,
                    "ai_analysis": ai_analysis,
                    "model_used": model_key,
                    "processing_timestamp": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"Error processing PDF with AI: {e}")
            return {"error": str(e)}

    def _analyze_text_with_ai(self, text_content: str, model_key: str) -> Dict[str, Any]:
        """Analyze text content with AI model"""
        try:
            # For now, provide basic analysis
            # In a full implementation, this would use the actual model for inference

            analysis = {
                "summary": self._generate_summary(text_content),
                "key_topics": self._extract_key_topics(text_content),
                "document_type": self._classify_document_type(text_content),
                "word_count": len(text_content.split()),
                "character_count": len(text_content),
                "estimated_reading_time": len(text_content.split()) // 200,  # ~200 words per minute
                "complexity_score": self._calculate_complexity_score(text_content),
            }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing text with AI: {e}")
            return {"error": str(e)}

    def _generate_summary(self, text: str) -> str:
        """Generate a basic summary of the text"""
        sentences = text.split(".")
        if len(sentences) <= 3:
            return text[:500] + "..." if len(text) > 500 else text

        # Simple summary: first few sentences + last sentence
        summary = ". ".join(sentences[:2]) + ". " + sentences[-1]
        return summary[:500] + "..." if len(summary) > 500 else summary

    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract key topics from text"""
        # Simple keyword extraction
        words = text.lower().split()
        word_freq = {}

        # Common stop words to ignore
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
        }

        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Return top 5 most frequent words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:5]]

    def _classify_document_type(self, text: str) -> str:
        """Classify the type of document"""
        text_lower = text.lower()

        if any(word in text_lower for word in ["contract", "agreement", "terms", "conditions"]):
            return "legal_document"
        elif any(word in text_lower for word in ["report", "analysis", "study", "research"]):
            return "report"
        elif any(word in text_lower for word in ["manual", "guide", "instructions", "how-to"]):
            return "manual"
        elif any(word in text_lower for word in ["invoice", "bill", "payment", "receipt"]):
            return "financial"
        elif any(word in text_lower for word in ["resume", "cv", "curriculum vitae"]):
            return "resume"
        else:
            return "general"

    def _calculate_complexity_score(self, text: str) -> float:
        """Calculate text complexity score (0-1)"""
        sentences = text.split(".")
        words = text.split()

        if not sentences or not words:
            return 0.0

        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)

        # Normalize scores
        complexity = (avg_sentence_length / 20.0 + avg_word_length / 8.0) / 2.0
        return min(1.0, max(0.0, complexity))

    def start_pdf_processing_service(self, port: int = 8080) -> bool:
        """Start the PDF processing service"""
        try:
            self.port = port
            self.lightweight_server.port = port
            self.lightweight_server.start_server()
            logger.info(f"PDF processing service started on port {port}")
            return True
        except Exception as e:
            logger.error(f"Error starting PDF processing service: {e}")
            return False

    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the PDF processing service"""
        return {
            "service_running": self.lightweight_server.running,
            "port": self.port,
            "models_loaded": list(self.lightweight_server.loaded_models.keys()),
            "temp_directory": str(self.temp_dir),
            "available_models": list(LIGHTWEIGHT_MODELS.keys()),
        }


def create_pdf_processor_api():
    """Create a simple API for PDF processing"""
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class PDFProcessorHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, processor=None, **kwargs):
            self.processor = processor
            super().__init__(*args, **kwargs)

        def do_POST(self):
            """Handle PDF processing requests"""
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            if path == "/process-pdf":
                self._handle_process_pdf()
            elif path == "/extract-text":
                self._handle_extract_text()
            else:
                self._send_response(404, {"error": "Endpoint not found"})

        def do_GET(self):
            """Handle status requests"""
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            if path == "/status":
                status = self.processor.get_service_status()
                self._send_response(200, status)
            else:
                self._send_response(404, {"error": "Endpoint not found"})

        def _handle_process_pdf(self):
            """Handle PDF processing with AI"""
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode("utf-8"))

                pdf_path = request_data.get("pdf_path")
                model_key = request_data.get("model_key")

                if not pdf_path:
                    self._send_response(400, {"error": "PDF path is required"})
                    return

                result = self.processor.process_pdf_with_ai(pdf_path, model_key)
                self._send_response(200, result)

            except Exception as e:
                self._send_response(500, {"error": str(e)})

        def _handle_extract_text(self):
            """Handle text extraction from PDF"""
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode("utf-8"))

                pdf_path = request_data.get("pdf_path")

                if not pdf_path:
                    self._send_response(400, {"error": "PDF path is required"})
                    return

                result = self.processor.extract_text_from_pdf(pdf_path)
                self._send_response(200, result)

            except Exception as e:
                self._send_response(500, {"error": str(e)})

        def _send_response(self, status_code, data):
            """Send JSON response"""
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

    return PDFProcessorHandler


if __name__ == "__main__":
    # Test the PDF processor
    processor = PDFProcessor()

    # Test with a sample PDF if available
    test_pdf = "test.pdf"
    if os.path.exists(test_pdf):
        result = processor.process_pdf_with_ai(test_pdf)
        print(json.dumps(result, indent=2))
    else:
        print("No test PDF found. Create a test.pdf file to test the processor.")
