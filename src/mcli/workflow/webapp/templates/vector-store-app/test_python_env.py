#!/usr/bin/env python3
"""
Test script to verify Python environment for Vector Store Manager
"""

import sys
import json

def test_imports():
    """Test if all required modules can be imported"""
    required_modules = [
        'torch',
        'sentence_transformers', 
        'transformers',
        'numpy',
        'faiss',
        'PyPDF2',
        'docx',
        'bs4',
        'pandas',
        'psutil'
    ]
    
    results = {}
    
    for module in required_modules:
        try:
            __import__(module)
            results[module] = "OK"
            print(f"✓ {module}: OK")
        except ImportError as e:
            results[module] = f"ERROR: {str(e)}"
            print(f"✗ {module}: ERROR - {str(e)}")
    
    return results

def test_torch():
    """Test PyTorch functionality"""
    try:
        import torch
        print(f"✓ PyTorch version: {torch.__version__}")
        print(f"✓ CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✓ CUDA device count: {torch.cuda.device_count()}")
        return True
    except Exception as e:
        print(f"✗ PyTorch test failed: {e}")
        return False

def test_sentence_transformers():
    """Test sentence-transformers functionality"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        test_text = "This is a test sentence."
        embedding = model.encode(test_text)
        print(f"✓ Sentence-transformers: OK (embedding shape: {embedding.shape})")
        return True
    except Exception as e:
        print(f"✗ Sentence-transformers test failed: {e}")
        return False

def test_faiss():
    """Test FAISS functionality"""
    try:
        import faiss
        import numpy as np
        
        # Create a simple index
        dimension = 384
        index = faiss.IndexFlatL2(dimension)
        
        # Add some test vectors
        vectors = np.random.random((10, dimension)).astype('float32')
        index.add(vectors)
        
        print(f"✓ FAISS: OK (index size: {index.ntotal})")
        return True
    except Exception as e:
        print(f"✗ FAISS test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Vector Store Manager - Python Environment Test")
    print("=" * 50)
    
    print("\n1. Testing module imports...")
    import_results = test_imports()
    
    print("\n2. Testing PyTorch...")
    torch_ok = test_torch()
    
    print("\n3. Testing sentence-transformers...")
    st_ok = test_sentence_transformers()
    
    print("\n4. Testing FAISS...")
    faiss_ok = test_faiss()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    all_imports_ok = all(status == "OK" for status in import_results.values())
    all_tests_ok = torch_ok and st_ok and faiss_ok
    
    if all_imports_ok and all_tests_ok:
        print("✓ All tests passed! Python environment is ready.")
        print("✓ You can now run the Vector Store Manager.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        print("✗ Run the fix_python_deps.sh script to resolve dependency issues.")
        sys.exit(1)

if __name__ == "__main__":
    main() 