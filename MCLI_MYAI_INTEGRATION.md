# MCLI + myAi Integration Guide

This guide describes the integration between the MCLI lightweight model service and the myAi Electron application for enhanced PDF processing with AI analysis.

## Overview

The integration provides:
- **AI-powered PDF analysis** using lightweight models
- **Enhanced text extraction** with multiple fallback methods
- **Document classification** and topic extraction
- **Complexity scoring** and reading time estimation
- **Seamless integration** with existing myAi workflow

## Architecture

```
┌─────────────────┐    HTTP API    ┌─────────────────┐
│   myAi App      │◄──────────────►│  MCLI Service   │
│  (Electron)     │                │  (FastAPI)      │
│                 │                │                 │
│ • PDF Upload    │                │ • PDF Processing│
│ • UI Display    │                │ • AI Analysis   │
│ • Vector Store  │                │ • Lightweight   │
│                 │                │   Models        │
└─────────────────┘                └─────────────────┘
```

## Features

### 🚀 AI-Powered PDF Processing
- **Automatic model selection** based on system capabilities
- **Enhanced text extraction** using PyMuPDF and PyPDF2
- **Document classification** (legal, report, manual, financial, resume)
- **Key topic extraction** with stop word filtering
- **Complexity scoring** based on sentence and word length
- **Reading time estimation** (~200 words per minute)

### 📊 Enhanced Document Information
- **AI analysis summary** for each document
- **Document type classification** with confidence
- **Key topics and themes** extracted automatically
- **Complexity metrics** for readability assessment
- **Processing metadata** with timestamps

### 🔄 Seamless Integration
- **Automatic fallback** to local processing if MCLI unavailable
- **Real-time status updates** via WebSocket
- **Enhanced UI** showing AI analysis results
- **Database storage** of AI analysis data

## Setup Instructions

### 1. Start MCLI Model Service

```bash
# Start the MCLI model service with lightweight models
mcli workflow model-service start

# Or start with specific port
mcli workflow model-service start --port 8000
```

### 2. Start myAi Application

```bash
# Navigate to myAi directory
cd ../myAi

# Install dependencies (if not already done)
npm install

# Start the application
npm start
```

### 3. Verify Integration

```bash
# Run the integration test
python test_mcli_integration.py
```

## API Endpoints

### MCLI Service Endpoints

#### Health Check
```http
GET http://localhost:8000/health
```

#### Lightweight Models
```http
GET http://localhost:8000/lightweight/models
POST http://localhost:8000/lightweight/models/{model_key}/download
```

#### PDF Processing
```http
POST http://localhost:8000/pdf/extract-text
{
  "pdf_path": "/path/to/document.pdf"
}

POST http://localhost:8000/pdf/process-with-ai
{
  "pdf_path": "/path/to/document.pdf",
  "model_key": "optional_model_key"
}

GET http://localhost:8000/pdf/status
```

### myAi Application Endpoints

#### Upload with MCLI Integration
```http
POST http://localhost:3004/api/upload
Content-Type: multipart/form-data

files: [PDF files]
```

Response includes MCLI status and AI analysis:
```json
{
  "success": true,
  "files": [...],
  "embeddings": [...],
  "mcli_status": {
    "status": "running",
    "url": "http://localhost:8000"
  }
}
```

## Usage Examples

### 1. Process PDF with AI Analysis

```bash
# Using MCLI CLI
mcli workflow model-service process-pdf document.pdf

# Using MCLI CLI with specific model
mcli workflow model-service process-pdf document.pdf --model bert-tiny

# Extract text only
mcli workflow model-service process-pdf document.pdf --extract-only
```

### 2. Start PDF Processing Service

```bash
# Start dedicated PDF processing service
mcli workflow model-service start-pdf-service --port 8080
```

### 3. Upload PDF through myAi Interface

1. Open myAi application
2. Click "Upload Documents"
3. Select PDF files
4. Watch real-time processing with AI analysis
5. View enhanced document information with AI insights

## Configuration

### MCLI Service Configuration

The MCLI service can be configured via environment variables:

```bash
# Model service configuration
export MCLI_MODEL_SERVICE_PORT=8000
export MCLI_MODELS_DIR="./models"
export MCLI_ENABLE_CORS=true

# Lightweight model configuration
export MCLI_LIGHTWEIGHT_PORT=8001
export MCLI_PDF_SERVICE_PORT=8002
```

### myAi Configuration

The myAi application automatically detects and integrates with MCLI:

```javascript
// MCLI service configuration in main.js
const MCLI_SERVICE_URL = 'http://localhost:8000';
const MCLI_PDF_SERVICE_URL = `${MCLI_SERVICE_URL}/pdf`;
const MCLI_LIGHTWEIGHT_URL = `${MCLI_SERVICE_URL}/lightweight`;
```

## Database Schema

### Enhanced Documents Table

The integration adds AI analysis data to the existing documents table:

```sql
ALTER TABLE documents ADD COLUMN ai_analysis TEXT;
```

The `ai_analysis` column contains JSON with:
- Document summary
- Key topics
- Document type classification
- Word count and complexity score
- Estimated reading time

## Troubleshooting

### MCLI Service Issues

**Service not starting:**
```bash
# Check if port is available
lsof -i :8000

# Start with different port
mcli workflow model-service start --port 8001
```

**Model download issues:**
```bash
# Check available models
mcli workflow model-service lightweight --list

# Download specific model
mcli workflow model-service lightweight --download bert-tiny
```

### myAi Integration Issues

**Connection refused:**
- Ensure MCLI service is running on port 8000
- Check firewall settings
- Verify network connectivity

**PDF processing fails:**
- Check if PDF libraries are installed
- Verify PDF file is not corrupted
- Check MCLI service logs

### Performance Optimization

**For large PDFs:**
- Increase timeout settings
- Use smaller lightweight models
- Process PDFs in batches

**For memory constraints:**
- Use CPU-only models
- Limit concurrent processing
- Monitor memory usage

## Development

### Adding New AI Models

1. Add model to `LIGHTWEIGHT_MODELS` in `lightweight_model_server.py`
2. Implement model-specific processing in `PDFProcessor`
3. Update API endpoints to support new models

### Extending AI Analysis

1. Modify `_analyze_text_with_ai` method in `PDFProcessor`
2. Add new analysis fields to database schema
3. Update frontend to display new analysis

### Custom Integration

The integration is modular and can be extended:

```python
# Custom PDF processor
from mcli_integration import EnhancedPDFProcessor

processor = EnhancedPDFProcessor("http://localhost:8000")
result = processor.process_pdf_for_vector_store("document.pdf")
```

## Monitoring and Logging

### MCLI Service Logs

```bash
# View MCLI service logs
tail -f logs/mcli_model_service.log

# Check service status
curl http://localhost:8000/health
```

### myAi Application Logs

```bash
# View myAi logs
tail -f app.log

# Check application status
curl http://localhost:3004/api/stats
```

## Security Considerations

- **Local processing only** - no data sent to external services
- **File validation** - PDF files validated before processing
- **Error handling** - graceful fallback to local processing
- **Resource limits** - timeout and memory constraints

## Performance Metrics

Typical performance on modern hardware:
- **PDF processing**: 1-5 seconds per page
- **AI analysis**: 2-10 seconds per document
- **Memory usage**: 100-500MB per model
- **Concurrent processing**: 2-5 documents simultaneously

## Future Enhancements

- **Batch processing** for multiple documents
- **Advanced AI models** with better accuracy
- **Custom model training** for specific domains
- **Cloud integration** for distributed processing
- **Real-time collaboration** features

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Run the integration test script
4. Verify service connectivity

## License

This integration is part of the MCLI project and follows the same licensing terms. 