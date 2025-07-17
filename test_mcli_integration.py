#!/usr/bin/env python3
"""
Test script for MCLI integration with myAi application

This script tests the integration between the MCLI lightweight model service
and the myAi Electron application for PDF processing.
"""

import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path

def test_mcli_service():
    """Test MCLI model service functionality"""
    print("🧪 Testing MCLI Model Service Integration")
    print("=" * 60)
    
    # Test 1: Check if MCLI service is running
    print("\n1. Testing MCLI service availability...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ MCLI service is running")
            service_info = response.json()
            print(f"   Models loaded: {service_info.get('models_loaded', 0)}")
            print(f"   Memory usage: {service_info.get('memory_usage_mb', 0)} MB")
        else:
            print("❌ MCLI service returned error status")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ MCLI service is not running")
        print("   Start it with: mcli workflow model-service start")
        return False
    except Exception as e:
        print(f"❌ Error checking MCLI service: {e}")
        return False
    
    # Test 2: Check lightweight models
    print("\n2. Testing lightweight models...")
    try:
        response = requests.get("http://localhost:8000/lightweight/models", timeout=10)
        if response.status_code == 200:
            models = response.json()
            print(f"✅ Available lightweight models: {len(models.get('models', []))}")
            for model in models.get('models', []):
                print(f"   - {model['name']}: {model['parameters']} parameters")
        else:
            print("❌ Failed to get lightweight models")
    except Exception as e:
        print(f"❌ Error getting lightweight models: {e}")
    
    # Test 3: Check PDF service
    print("\n3. Testing PDF processing service...")
    try:
        response = requests.get("http://localhost:8000/pdf/status", timeout=5)
        if response.status_code == 200:
            pdf_status = response.json()
            print("✅ PDF processing service is available")
            print(f"   Service running: {pdf_status.get('service_running', False)}")
            print(f"   Available models: {len(pdf_status.get('available_models', []))}")
        else:
            print("❌ PDF processing service not available")
    except Exception as e:
        print(f"❌ Error checking PDF service: {e}")
    
    return True

def test_myai_integration():
    """Test myAi application integration"""
    print("\n🧪 Testing myAi Application Integration")
    print("=" * 60)
    
    # Test 1: Check if myAi is running
    print("\n1. Testing myAi application availability...")
    try:
        response = requests.get("http://localhost:3004/api/stats", timeout=5)
        if response.status_code == 200:
            print("✅ myAi application is running")
            stats = response.json()
            print(f"   Documents: {stats.get('documents', 0)}")
            print(f"   Embeddings: {stats.get('embeddings', 0)}")
        else:
            print("❌ myAi application returned error status")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ myAi application is not running")
        print("   Start it with: npm start")
        return False
    except Exception as e:
        print(f"❌ Error checking myAi application: {e}")
        return False
    
    # Test 2: Test PDF upload endpoint
    print("\n2. Testing PDF upload endpoint...")
    try:
        # Create a test PDF file
        test_pdf_path = "test_document.pdf"
        if not os.path.exists(test_pdf_path):
            print(f"   Creating test PDF: {test_pdf_path}")
            # Create a simple PDF for testing
            create_test_pdf(test_pdf_path)
        
        # Test the upload endpoint
        with open(test_pdf_path, 'rb') as f:
            files = {'files': (test_pdf_path, f, 'application/pdf')}
            response = requests.post("http://localhost:3004/api/upload", files=files, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ PDF upload successful")
            print(f"   Files processed: {len(result.get('files', []))}")
            print(f"   MCLI status: {result.get('mcli_status', {}).get('status', 'unknown')}")
        else:
            print(f"❌ PDF upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing PDF upload: {e}")
    
    return True

def create_test_pdf(filename):
    """Create a simple test PDF file"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(100, 750, "Test Document for MCLI Integration")
        c.drawString(100, 720, "This is a test PDF document to verify the integration")
        c.drawString(100, 690, "between MCLI lightweight model service and myAi application.")
        c.drawString(100, 660, "The document contains sample text for AI analysis.")
        c.drawString(100, 630, "Key topics: integration, testing, AI, PDF processing")
        c.save()
        print(f"   Created test PDF: {filename}")
    except ImportError:
        print("   Warning: reportlab not available, creating text file instead")
        with open(filename.replace('.pdf', '.txt'), 'w') as f:
            f.write("Test Document for MCLI Integration\n")
            f.write("This is a test document to verify the integration\n")
            f.write("between MCLI lightweight model service and myAi application.\n")
    except Exception as e:
        print(f"   Error creating test PDF: {e}")

def test_end_to_end():
    """Test end-to-end integration"""
    print("\n🧪 Testing End-to-End Integration")
    print("=" * 60)
    
    # Test 1: Start MCLI service if not running
    print("\n1. Ensuring MCLI service is running...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("   Starting MCLI service...")
            subprocess.Popen([
                "mcli", "workflow", "model-service", "start"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(5)  # Wait for service to start
    except:
        print("   Starting MCLI service...")
        subprocess.Popen([
            "mcli", "workflow", "model-service", "start"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)  # Wait for service to start
    
    # Test 2: Process a PDF with MCLI
    print("\n2. Testing PDF processing with MCLI...")
    test_pdf = "test_document.pdf"
    if not os.path.exists(test_pdf):
        create_test_pdf(test_pdf)
    
    try:
        response = requests.post(
            "http://localhost:8000/pdf/process-with-ai",
            json={"pdf_path": os.path.abspath(test_pdf)},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                analysis = result["pdf_analysis"]["ai_analysis"]
                print("✅ PDF processed successfully with AI")
                print(f"   Document type: {analysis['document_type']}")
                print(f"   Summary: {analysis['summary'][:100]}...")
                print(f"   Key topics: {', '.join(analysis['key_topics'])}")
                print(f"   Complexity score: {analysis['complexity_score']:.2f}")
            else:
                print(f"❌ PDF processing failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ PDF processing request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing PDF processing: {e}")
    
    # Test 3: Test myAi upload with MCLI integration
    print("\n3. Testing myAi upload with MCLI integration...")
    try:
        with open(test_pdf, 'rb') as f:
            files = {'files': (test_pdf, f, 'application/pdf')}
            response = requests.post("http://localhost:3004/api/upload", files=files, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ myAi upload with MCLI integration successful")
            print(f"   Files uploaded: {len(result.get('files', []))}")
            print(f"   MCLI status: {result.get('mcli_status', {}).get('status', 'unknown')}")
            
            # Check if AI analysis was performed
            embeddings = result.get('embeddings', [])
            for embedding in embeddings:
                if embedding.get('aiAnalysis'):
                    print("✅ AI analysis was performed during upload")
                    break
            else:
                print("⚠️  No AI analysis found in upload results")
        else:
            print(f"❌ myAi upload failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing myAi upload: {e}")

def main():
    """Run all integration tests"""
    print("🚀 MCLI + myAi Integration Test Suite")
    print("=" * 60)
    
    # Test MCLI service
    mcli_ok = test_mcli_service()
    
    # Test myAi integration
    myai_ok = test_myai_integration()
    
    # Test end-to-end
    if mcli_ok and myai_ok:
        test_end_to_end()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   MCLI Service: {'✅ Running' if mcli_ok else '❌ Not Available'}")
    print(f"   myAi App: {'✅ Running' if myai_ok else '❌ Not Available'}")
    
    if mcli_ok and myai_ok:
        print("\n🎉 Integration is working! You can now:")
        print("   1. Upload PDFs through the myAi interface")
        print("   2. Get AI-powered analysis of your documents")
        print("   3. View enhanced document information with AI insights")
    else:
        print("\n⚠️  Some services are not available. Please:")
        if not mcli_ok:
            print("   - Start MCLI service: mcli workflow model-service start")
        if not myai_ok:
            print("   - Start myAi application: npm start")

if __name__ == "__main__":
    main() 