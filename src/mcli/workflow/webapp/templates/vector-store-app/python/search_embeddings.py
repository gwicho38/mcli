#!/usr/bin/env python3
"""
Search embeddings in the vector store
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
    # Fallback if import fails
    print(json.dumps([]))
    sys.exit(1)

def main():
    if len(sys.argv) < 4:
        print(json.dumps([]))
        return
    
    query = sys.argv[1]
    top_k = int(sys.argv[2])
    exact_match = sys.argv[3].lower() == 'true'
    vector_store_path = sys.argv[4]
    
    try:
        # Initialize vector store manager
        vsm = VectorStoreManager(vector_store_path)
        
        # Load model if not already loaded
        if vsm.model is None:
            vsm.load_model()
        
        # Perform search
        if exact_match:
            # For exact match, we'll do a simple text search
            results = vsm.search_exact(query, top_k)
        else:
            # For semantic search, use embedding similarity
            results = vsm.search_similar(query, top_k)
        
        # Format results for JSON output
        formatted_results = []
        for result in results:
            formatted_results.append({
                'document_id': result.get('document_id', ''),
                'filename': result.get('filename', ''),
                'text_chunk': result.get('text_chunk', ''),
                'similarity_score': result.get('similarity_score', 0.0),
                'chunk_index': result.get('chunk_index', 0)
            })
        
        print(json.dumps(formatted_results))
        
    except Exception as e:
        print(json.dumps([]))
        sys.exit(1)

if __name__ == "__main__":
    main() 