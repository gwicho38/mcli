# MCLI Lightweight Model Server Integration

This document describes the integration of the lightweight model server with the main MCLI model service, providing ultra-efficient model serving capabilities for resource-constrained environments.

## Overview

The lightweight model server has been fully integrated into the existing MCLI model service, providing:

- **Ultra-small models** (under 100M parameters)
- **Minimal dependencies** (no heavy ML frameworks required)
- **Automatic system analysis** and model recommendation
- **Direct download** from HuggingFace URLs
- **Simple HTTP API** for model serving
- **CLI integration** with existing MCLI commands

## Features

### 🚀 Ultra-Efficient Models
- **BERT Tiny** (4.4M parameters, 18MB)
- **Tiny DistilBERT** (22M parameters, 88MB)
- **DialoGPT Tiny** (33M parameters, 132MB)
- **DistilBERT Base** (66M parameters, 260MB)
- **DialoGPT Small** (117M parameters, 470MB)

### 🔧 System Analysis
- Automatic CPU core detection
- Memory usage analysis
- Disk space checking
- Model recommendation based on system capabilities

### 📥 Smart Downloading
- Progress tracking during downloads
- Automatic model file organization
- Error handling and retry logic
- Download verification

### 🌐 Simple HTTP API
- RESTful endpoints for model management
- JSON-based request/response format
- CORS support for web applications
- Health check endpoints

## Integration with Main Model Service

### API Endpoints

The lightweight server is accessible through the main model service API:

#### List Available Models
```bash
GET /lightweight/models
```

Response:
```json
{
  "models": {
    "prajjwal1/bert-tiny": {
      "name": "BERT Tiny",
      "description": "Tiny BERT model, 4.4M parameters",
      "parameters": "4.4M",
      "size_mb": 18,
      "efficiency_score": 10.0,
      "model_type": "text-classification"
    }
  },
  "downloaded": ["prajjwal1/bert-tiny"],
  "loaded": ["prajjwal1/bert-tiny"]
}
```

#### Download Model
```bash
POST /lightweight/models/{model_key}/download
```

Response:
```json
{
  "status": "downloaded",
  "model": "prajjwal1/bert-tiny"
}
```

#### Start Lightweight Server
```bash
POST /lightweight/start
```

Response:
```json
{
  "status": "started",
  "port": 8081,
  "url": "http://localhost:8081"
}
```

#### Get Server Status
```bash
GET /lightweight/status
```

Response:
```json
{
  "running": true,
  "port": 8081,
  "loaded_models": ["prajjwal1/bert-tiny"],
  "system_info": {
    "cpu_count": 8,
    "memory_gb": 16.0,
    "disk_free_gb": 100.0,
    "models_loaded": 1,
    "total_models_size_mb": 18
  }
}
```

### CLI Commands

#### Lightweight Model Management
```bash
# List available models
mcli model-service lightweight --list

# Download recommended model for your system
mcli model-service lightweight --auto

# Download specific model
mcli model-service lightweight --download prajjwal1/bert-tiny

# Start lightweight server
mcli model-service lightweight --start-server --port 8080
```

#### Standalone Lightweight Server
```bash
# Run with auto-selected model
mcli model-service lightweight-run --auto --port 8080

# Run with specific model
mcli model-service lightweight-run --model prajjwal1/bert-tiny --port 8080

# List available models
mcli model-service lightweight-run --list-models

# Download only (don't start server)
mcli model-service lightweight-run --download-only --auto
```

## Usage Examples

### 1. Quick Start with Auto-Recommendation

```bash
# Start the main model service
mcli model-service start --port 8000

# In another terminal, download and start lightweight server
mcli model-service lightweight --auto --start-server --port 8080
```

### 2. API Usage

```python
import requests

# List lightweight models
response = requests.get("http://localhost:8000/lightweight/models")
models = response.json()

# Download a model
response = requests.post("http://localhost:8000/lightweight/models/prajjwal1/bert-tiny/download")
result = response.json()

# Start lightweight server
response = requests.post("http://localhost:8000/lightweight/start")
server_info = response.json()

# Use the lightweight server
lightweight_url = f"http://localhost:{server_info['port']}"
response = requests.get(f"{lightweight_url}/models")
```

### 3. System Integration

```python
from mcli.workflow.model_service.model_service import ModelService

# Create service instance
service = ModelService()

# Get system analysis
system_info = service.lightweight_server.get_system_info()
recommended_model = service.lightweight_server.recommend_model()

# Download recommended model
success = service.lightweight_server.download_and_load_model(recommended_model)

# Start lightweight server
service.lightweight_server.start_server()
```

## Architecture

### Component Integration

```
MCLI Model Service
├── Main Model Service (port 8000)
│   ├── Full-featured model management
│   ├── Heavy model support
│   └── Advanced inference capabilities
└── Lightweight Server (port 8001)
    ├── Ultra-small models
    ├── Minimal dependencies
    └── Simple HTTP API
```

### File Structure

```
src/mcli/workflow/model_service/
├── model_service.py              # Main service with lightweight integration
├── lightweight_model_server.py   # Lightweight server implementation
├── lightweight_test.py          # Standalone lightweight server test
├── test_integration.py          # Integration test script
├── LIGHTWEIGHT_README.md        # Lightweight server documentation
└── INTEGRATION_README.md        # This integration documentation
```

## Configuration

### Environment Variables

```bash
# Model service configuration
MCLI_MODEL_SERVICE_HOST=0.0.0.0
MCLI_MODEL_SERVICE_PORT=8000
MCLI_MODEL_SERVICE_MODELS_DIR=./models

# Lightweight server configuration
MCLI_LIGHTWEIGHT_PORT=8080
MCLI_LIGHTWEIGHT_MODELS_DIR=./models/lightweight
```

### Configuration File

```toml
[model_service]
host = "0.0.0.0"
port = 8000
models_dir = "./models"
enable_cors = true
log_level = "INFO"

[lightweight]
port = 8080
models_dir = "./models/lightweight"
auto_start = false
```

## Testing

### Run Integration Tests

```bash
# Test the integration
python src/mcli/workflow/model_service/test_integration.py

# Test standalone lightweight server
python src/mcli/workflow/model_service/lightweight_test.py

# Test main model service with lightweight features
mcli model-service start --port 8000
```

### Test API Endpoints

```bash
# Test lightweight models endpoint
curl http://localhost:8000/lightweight/models

# Test model download
curl -X POST http://localhost:8000/lightweight/models/prajjwal1/bert-tiny/download

# Test lightweight server start
curl -X POST http://localhost:8000/lightweight/start

# Test lightweight server status
curl http://localhost:8000/lightweight/status
```

## Performance Characteristics

### Model Sizes and Performance

| Model | Parameters | Size | Memory | Speed | Use Case |
|-------|------------|------|--------|-------|----------|
| BERT Tiny | 4.4M | 18MB | ~50MB | ⚡⚡⚡ | Classification |
| Tiny DistilBERT | 22M | 88MB | ~100MB | ⚡⚡⚡ | Classification |
| DialoGPT Tiny | 33M | 132MB | ~150MB | ⚡⚡⚡ | Generation |
| DistilBERT Base | 66M | 260MB | ~300MB | ⚡⚡ | Classification |
| DialoGPT Small | 117M | 470MB | ~500MB | ⚡⚡ | Generation |

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 1GB
- **Disk**: 100MB free space
- **Network**: Internet connection for downloads

#### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 4GB+
- **Disk**: 1GB+ free space
- **Network**: Stable internet connection

## Troubleshooting

### Common Issues

#### 1. Download Failures
```bash
# Check network connectivity
curl -I https://huggingface.co

# Check disk space
df -h

# Retry with verbose output
mcli model-service lightweight --download prajjwal1/bert-tiny --verbose
```

#### 2. Port Conflicts
```bash
# Check if ports are in use
lsof -i :8000
lsof -i :8080

# Use different ports
mcli model-service start --port 8001
mcli model-service lightweight --start-server --port 8081
```

#### 3. Memory Issues
```bash
# Check available memory
free -h

# Use smaller models
mcli model-service lightweight --download prajjwal1/bert-tiny
```

### Debug Mode

```bash
# Enable debug logging
export MCLI_LOG_LEVEL=DEBUG

# Run with debug output
mcli model-service lightweight --download prajjwal1/bert-tiny --debug
```

## Future Enhancements

### Planned Features

1. **More Model Types**
   - Image classification models
   - Translation models
   - Speech recognition models

2. **Advanced Features**
   - Model quantization
   - Batch processing
   - Streaming responses
   - Model versioning

3. **Integration Improvements**
   - Kubernetes deployment
   - Docker containerization
   - Load balancing
   - Auto-scaling

### Contributing

To contribute to the lightweight model server integration:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

This integration is part of the MCLI project and follows the same licensing terms.

## Support

For support with the lightweight model server integration:

1. Check the troubleshooting section
2. Review the test scripts
3. Open an issue on GitHub
4. Contact the development team

---

**Note**: The lightweight model server is designed for resource-constrained environments and provides a simplified API compared to the full model service. For production use with larger models, consider using the main model service with full-featured capabilities. 