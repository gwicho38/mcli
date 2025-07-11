#!/usr/bin/env python3
"""
Text extraction from various file formats
"""

import sys
import json
import os
from pathlib import Path

# Add the current directory to Python path to import VectorStoreManager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from generate_embeddings import VectorStoreManager
except ImportError:
    VectorStoreManager = None
    # Do not print or exit here

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"text": "", "error": "Insufficient arguments"}))
        return
    
    file_path = sys.argv[1]
    mime_type = sys.argv[2]
    vector_store_path = sys.argv[3] if len(sys.argv) > 3 else "/tmp/vector-store"
    
    if VectorStoreManager is None:
        print(json.dumps({"text": "", "error": "VectorStoreManager import failed"}))
        sys.exit(1)
    try:
        # Initialize vector store manager
        vsm = VectorStoreManager(vector_store_path)
        # Extract text from file
        extracted_text = vsm.extract_text_from_file(file_path, mime_type)
        # Return result as JSON
        result = {
            "text": extracted_text,
            "file_path": file_path,
            "mime_type": mime_type,
            "text_length": len(extracted_text)
        }
        print(json.dumps(result))
    except Exception as e:
        error_result = {
            "text": "",
            "error": str(e),
            "file_path": file_path,
            "mime_type": mime_type
        }
        print(json.dumps(error_result))

if __name__ == "__main__":
    main() 