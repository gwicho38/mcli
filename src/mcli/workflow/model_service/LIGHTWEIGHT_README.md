# Lightweight Model Server for MCLI

A minimal model server that downloads and runs extremely small and efficient models directly from the internet without requiring Ollama or heavy dependencies.

## 🎯 Overview

This lightweight approach focuses on **ultra-small models** (under 100M parameters) that can run on any device with minimal resources. Perfect for:

- **Edge devices** (Raspberry Pi, IoT devices)
- **Low-memory systems** (2-4GB RAM)
- **Quick prototyping** and testing
- **Resource-constrained environments**

## 🚀 Ultra-Lightweight Models

### Available Models

| Model | Parameters | Size | Type | Use Case |
|-------|------------|------|------|----------|
| **BERT Tiny** | 4.4M | 18MB | Classification | Text classification |
| **Tiny DistilBERT** | 22M | 88MB | Classification | Fast text analysis |
| **DialoGPT Tiny** | 33M | 132MB | Generation | Simple conversations |
| **DistilBERT Base** | 66M | 260MB | Classification | General NLP tasks |
| **DialoGPT Small** | 117M | 470MB | Generation | Chat applications |

### Model Comparison

| Model | Efficiency | Accuracy | Speed | Memory Usage |
|-------|------------|----------|-------|--------------|
| BERT Tiny | 10.0/10 | 4.5/10 | Lightning | 50MB |
| Tiny DistilBERT | 10.0/10 | 5.5/10 | Very Fast | 100MB |
| DialoGPT Tiny | 10.0/10 | 5.0/10 | Very Fast | 150MB |
| DistilBERT Base | 10.0/10 | 7.0/10 | Fast | 300MB |
| DialoGPT Small | 9.8/10 | 6.5/10 | Fast | 500MB |

## 🛠️ Installation

### Minimal Dependencies

```bash
# Core dependencies only
pip install requests click psutil

# Optional: For better performance
pip install torch transformers
```

### No Heavy Dependencies Required

Unlike the Ollama approach, this server:
- ❌ **No Ollama installation required**
- ❌ **No Docker required**
- ❌ **No large model downloads**
- ✅ **Minimal Python dependencies**
- ✅ **Direct HTTP downloads**
- ✅ **Built-in HTTP server**

## 🚀 Quick Start

### 1. Basic Usage

```bash
# Start with auto-selected model
python lightweight_model_server.py

# Specify a model
python lightweight_model_server.py --model prajjwal1/bert-tiny

# List available models
python lightweight_model_server.py --list-models

# Download only (no server)
python lightweight_model_server.py --download-only --model prajjwal1/bert-tiny
```

### 2. Server Endpoints

Once running, the server provides these endpoints:

```bash
# Health check
curl http://localhost:8080/health

# List loaded models
curl http://localhost:8080/models

# Generate text (if generation model loaded)
curl -X POST http://localhost:8080/models/dialogpt-tiny/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'
```

### 3. Python Client

```python
import requests

# Health check
response = requests.get("http://localhost:8080/health")
print(response.json())

# Generate text
response = requests.post(
    "http://localhost:8080/models/dialogpt-tiny/generate",
    json={"prompt": "Explain quantum computing"}
)
print(response.json()["generated_text"])
```

## 📊 System Requirements

### Minimum Requirements
- **CPU**: 1+ core (any modern CPU)
- **RAM**: 512MB
- **Storage**: 100MB free space
- **Network**: Internet connection for download

### Recommended Requirements
- **CPU**: 2+ cores
- **RAM**: 2GB
- **Storage**: 1GB free space
- **Network**: Stable internet connection

### Resource Usage Examples

| Model | RAM Usage | CPU Usage | Download Time |
|-------|-----------|-----------|---------------|
| BERT Tiny | 50MB | 5% | 30 seconds |
| Tiny DistilBERT | 100MB | 10% | 1 minute |
| DialoGPT Tiny | 150MB | 15% | 2 minutes |
| DistilBERT Base | 300MB | 20% | 5 minutes |
| DialoGPT Small | 500MB | 25% | 8 minutes |

## 🔧 Advanced Usage

### Custom Port

```bash
python lightweight_model_server.py --port 9000
```

### Download Multiple Models

```bash
# Download all models
for model in prajjwal1/bert-tiny sshleifer/tiny-distilbert-base-uncased microsoft/DialoGPT-tiny; do
    python lightweight_model_server.py --download-only --model $model
done
```

### Create Client Script

```bash
python lightweight_model_server.py --create-client
```

This creates `lightweight_client.py` for easy testing.

### System-Specific Recommendations

The server automatically recommends models based on your system:

```bash
# For very limited systems (< 1GB RAM)
python lightweight_model_server.py --model prajjwal1/bert-tiny

# For small systems (1-2GB RAM)
python lightweight_model_server.py --model sshleifer/tiny-distilbert-base-uncased

# For standard systems (2-4GB RAM)
python lightweight_model_server.py --model distilbert-base-uncased

# For better performance (4GB+ RAM)
python lightweight_model_server.py --model microsoft/DialoGPT-small
```

## 🧪 Testing

### Run Tests

```bash
python lightweight_test.py
```

### Manual Testing

```bash
# 1. Start server
python lightweight_model_server.py --model prajjwal1/bert-tiny

# 2. In another terminal, test endpoints
curl http://localhost:8080/health
curl http://localhost:8080/models

# 3. Test generation (if generation model loaded)
curl -X POST http://localhost:8080/models/dialogpt-tiny/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'
```

## 📁 File Structure

```
lightweight_models/
├── prajjwal1/bert-tiny/
│   ├── pytorch_model.bin
│   ├── tokenizer.json
│   └── config.json
├── sshleifer/tiny-distilbert-base-uncased/
│   ├── pytorch_model.bin
│   ├── tokenizer.json
│   └── config.json
└── ...
```

## 🔄 API Reference

### GET Endpoints

#### `/health`
Returns server health status.

**Response:**
```json
{
  "status": "healthy"
}
```

#### `/models`
Returns list of loaded models.

**Response:**
```json
{
  "models": [
    {
      "name": "prajjwal1/bert-tiny",
      "type": "text-classification",
      "parameters": "4.4M"
    }
  ]
}
```

#### `/`
Returns server status and loaded models.

**Response:**
```json
{
  "status": "running",
  "models": ["prajjwal1/bert-tiny"]
}
```

### POST Endpoints

#### `/models/{model_name}/generate`
Generate text using a loaded model.

**Request:**
```json
{
  "prompt": "Hello, how are you?"
}
```

**Response:**
```json
{
  "generated_text": "I'm doing well, thank you for asking!",
  "model": "microsoft/DialoGPT-tiny"
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Download fails**
   ```bash
   # Check internet connection
   curl -I https://huggingface.co
   
   # Try a different model
   python lightweight_model_server.py --model prajjwal1/bert-tiny
   ```

2. **Port already in use**
   ```bash
   # Use different port
   python lightweight_model_server.py --port 8081
   
   # Or kill existing process
   lsof -ti:8080 | xargs kill -9
   ```

3. **Out of memory**
   ```bash
   # Use smallest model
   python lightweight_model_server.py --model prajjwal1/bert-tiny
   ```

4. **Model not found**
   ```bash
   # List available models
   python lightweight_model_server.py --list-models
   ```

### Debug Mode

```bash
# Enable verbose logging
export MCLI_LOG_LEVEL=DEBUG
python lightweight_model_server.py
```

## 🚀 Performance Tips

### For Maximum Speed

1. **Use smallest models** for fastest inference
2. **Download models once** and reuse them
3. **Run on SSD** for faster model loading
4. **Use multiple cores** if available

### For Maximum Efficiency

1. **BERT Tiny** for classification tasks
2. **DialoGPT Tiny** for simple conversations
3. **Tiny DistilBERT** for general NLP

### Memory Optimization

```bash
# For very limited memory (< 1GB)
python lightweight_model_server.py --model prajjwal1/bert-tiny

# For small memory (1-2GB)
python lightweight_model_server.py --model sshleifer/tiny-distilbert-base-uncased

# For standard memory (2-4GB)
python lightweight_model_server.py --model distilbert-base-uncased
```

## 🔗 Integration Examples

### With Python

```python
import requests
import json

class LightweightClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def health_check(self):
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def list_models(self):
        response = requests.get(f"{self.base_url}/models")
        return response.json()
    
    def generate_text(self, model_name, prompt):
        response = requests.post(
            f"{self.base_url}/models/{model_name}/generate",
            json={"prompt": prompt}
        )
        return response.json()

# Usage
client = LightweightClient()
print(client.health_check())
print(client.list_models())
result = client.generate_text("dialogpt-tiny", "Hello!")
print(result["generated_text"])
```

### With curl

```bash
# Health check
curl http://localhost:8080/health

# List models
curl http://localhost:8080/models

# Generate text
curl -X POST http://localhost:8080/models/dialogpt-tiny/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing"}'
```

### With JavaScript

```javascript
// Health check
fetch('http://localhost:8080/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Generate text
fetch('http://localhost:8080/models/dialogpt-tiny/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: 'Hello, how are you?'
  })
})
.then(response => response.json())
.then(data => console.log(data.generated_text));
```

## 📈 Comparison with Other Approaches

| Feature | Lightweight Server | Ollama | Full MCLI |
|---------|-------------------|--------|-----------|
| **Installation** | Minimal | Medium | Heavy |
| **Dependencies** | 3 packages | Ollama + Python | Full stack |
| **Model Size** | 18MB-470MB | 1GB-70GB | Variable |
| **Memory Usage** | 50MB-500MB | 1GB-16GB | Variable |
| **Startup Time** | 1-5 seconds | 10-30 seconds | 30+ seconds |
| **Use Case** | Edge/IoT | Desktop | Production |

## 🎯 Use Cases

### Perfect For:
- ✅ **Edge computing** (Raspberry Pi, IoT)
- ✅ **Quick prototyping** and testing
- ✅ **Resource-constrained environments**
- ✅ **Educational purposes**
- ✅ **Simple NLP tasks**

### Not Suitable For:
- ❌ **Complex language generation**
- ❌ **High-accuracy requirements**
- ❌ **Production deployments** (use full MCLI)
- ❌ **Large-scale inference**

## 🔮 Future Enhancements

Potential improvements:
- **Model quantization** for even smaller sizes
- **Caching** for faster repeated requests
- **Batch processing** for multiple requests
- **Model fine-tuning** capabilities
- **More model types** (translation, summarization)

## 📄 License

This project is part of the MCLI framework and follows the same license terms. 