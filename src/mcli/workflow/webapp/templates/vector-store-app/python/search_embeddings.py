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
        print(json.dumps({"error": "Insufficient arguments", "code": "INVALID_ARGS"}))
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
            try:
                results = vsm.search_similar(query, top_k)
            except RuntimeError as e:
                # Handle insufficient embeddings error
                error_msg = str(e)
                if "Only" in error_msg and "embeddings found" in error_msg:
                    print(json.dumps({
                        "error": error_msg,
                        "code": "NOT_ENOUGH_EMBEDDINGS",
                        "suggestion": "Try exact search instead or add more documents",
                        "status": "semantic_search_unavailable"
                    }))
                else:
                    print(json.dumps({
                        "error": error_msg,
                        "code": "VECTOR_INDEX_ERROR",
                        "status": "error"
                    }))
                sys.exit(2)
        
        # Format results for JSON output
        formatted_results = []
        for result in results:
            formatted_results.append({
                'document_id': result.get('document_id', ''),
                'filename': result.get('document_name', ''),
                'text_chunk': result.get('text_chunk', ''),
                'similarity_score': result.get('similarity_score', 0.0),
                'chunk_index': result.get('chunk_index', 0),
                'rank': result.get('rank', 0)
            })
        
        print(json.dumps({
            "results": formatted_results,
            "count": len(formatted_results),
            "status": "success"
        }))
        
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "code": "UNKNOWN_ERROR",
            "status": "error"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main() 