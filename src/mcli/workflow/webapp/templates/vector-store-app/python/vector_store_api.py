#!/usr/bin/env python3
"""
Vector Store API - Sample FastAPI implementation
Demonstrates proper error handling for insufficient embeddings
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

try:
    from generate_embeddings import VectorStoreManager
except ImportError as e:
    print(f"Error importing VectorStoreManager: {e}")
    sys.exit(1)

# FastAPI imports
try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    print("FastAPI not available. Install with: pip install fastapi uvicorn")
    sys.exit(1)

# Pydantic models for API
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    search_type: str = "semantic"  # "semantic" or "exact"

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    count: int
    search_type: str
    status: str

class ErrorResponse(BaseModel):
    error: str
    code: str
    suggestion: Optional[str] = None
    status: str

class StatusResponse(BaseModel):
    available: bool
    embedding_count: int
    minimum_required: int
    message: str
    status: str

# Initialize FastAPI app
app = FastAPI(
    title="Vector Store API",
    description="API for semantic and exact search in document vector store",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global vector store manager
vsm = None

def get_vector_store_manager():
    """Get or initialize the vector store manager"""
    global vsm
    if vsm is None:
        # You can configure this path via environment variable
        vector_store_path = Path("./vector-store")
        vsm = VectorStoreManager(str(vector_store_path))
    return vsm

@app.on_event("startup")
async def startup_event():
    """Initialize vector store on startup"""
    try:
        vsm = get_vector_store_manager()
        # Load model
        if vsm.model is None:
            vsm.load_model()
        print("✅ Vector store API initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing vector store: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Vector Store API", "version": "1.0.0"}

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get vector store status and semantic search availability"""
    try:
        vsm = get_vector_store_manager()
        status = vsm.get_semantic_search_status()
        status["status"] = "success"
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search documents using semantic or exact search"""
    try:
        vsm = get_vector_store_manager()
        
        if request.search_type == "semantic":
            try:
                results = vsm.search_similar(request.query, request.top_k)
                return SearchResponse(
                    results=results,
                    count=len(results),
                    search_type="semantic",
                    status="success"
                )
            except RuntimeError as e:
                error_msg = str(e)
                if "Only" in error_msg and "embeddings found" in error_msg:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": error_msg,
                            "code": "NOT_ENOUGH_EMBEDDINGS",
                            "suggestion": "Try exact search instead or add more documents",
                            "status": "semantic_search_unavailable"
                        }
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": error_msg,
                            "code": "VECTOR_INDEX_ERROR",
                            "status": "error"
                        }
                    )
        else:
            # Exact search
            results = vsm.search_exact(request.query, request.top_k)
            return SearchResponse(
                results=results,
                count=len(results),
                search_type="exact",
                status="success"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "code": "UNKNOWN_ERROR",
                "status": "error"
            }
        )

@app.get("/search", response_model=SearchResponse)
async def search_documents_get(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(10, description="Number of results to return"),
    search_type: str = Query("semantic", description="Search type: semantic or exact")
):
    """Search documents using GET method"""
    request = SearchRequest(query=query, top_k=top_k, search_type=search_type)
    return await search_documents(request)

@app.get("/documents")
async def list_documents():
    """List all documents in the vector store"""
    try:
        vsm = get_vector_store_manager()
        conn = vsm.db_path.parent / "vector_store.db"
        
        import sqlite3
        db_conn = sqlite3.connect(conn)
        cursor = db_conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, original_name, file_size, mime_type, 
                   upload_date, embedding_count, processing_status
            FROM documents
            ORDER BY created_at DESC
        ''')
        
        documents = []
        for row in cursor.fetchall():
            documents.append({
                "id": row[0],
                "filename": row[1],
                "original_name": row[2],
                "file_size": row[3],
                "mime_type": row[4],
                "upload_date": row[5],
                "embedding_count": row[6],
                "processing_status": row[7]
            })
        
        db_conn.close()
        
        return {
            "documents": documents,
            "count": len(documents),
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "code": "DATABASE_ERROR",
                "status": "error"
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 