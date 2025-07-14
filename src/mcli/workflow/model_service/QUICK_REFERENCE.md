# Model Service Quick Reference

## 🚀 Quick Start

### 1. Setup Environment with uv
```bash
# Ensure you're in the mcli project root
cd /path/to/mcli

# Install dependencies with uv
uv pip install huggingface-hub requests fastapi uvicorn
uv pip install torch transformers accelerate sentencepiece protobuf
uv pip install numpy pillow psutil python-multipart

# Or install all at once
uv pip install .[model-service]
```

### 2. Download and Setup Phi-2 (Recommended)
```bash
# Install huggingface-hub with uv
uv pip install huggingface-hub

# Download Phi-2
huggingface-cli download microsoft/phi-2 --local-dir ./models/phi-2

# Start service
mcli workflow model-service start --port 8000

# Add model
mcli workflow model-service add-model ./models/phi-2 --name "Phi-2" --type "text-generation"
```

### 3. Test Your Model
```bash
# Check service status
mcli workflow model-service status

# Test via API
curl -X POST http://localhost:8000/models/MODEL_ID/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'
```

## 📋 Essential Commands

### Service Management
```bash
# Start service
mcli workflow model-service start --port 8000

# Stop service
mcli workflow model-service stop

# Check status
mcli workflow model-service status
```

### Model Management
```bash
# Check service status (shows models)
mcli workflow model-service status

# Add model
mcli workflow model-service add-model ./models/phi-2 --name "Phi-2" --type "text-generation"

# Update model
mcli workflow model-service update-model MODEL_ID --temperature 0.8

# Remove model
mcli workflow model-service remove-model MODEL_ID
```

### Inference via API
```bash
# Generate text
curl -X POST http://localhost:8000/models/MODEL_ID/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Your prompt here"}'

# Classify text
curl -X POST http://localhost:8000/models/MODEL_ID/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a positive review"}'

# Translate text
curl -X POST http://localhost:8000/models/MODEL_ID/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "source_lang": "en", "target_lang": "es"}'
```

## 🎯 Model Recommendations

| Model | Size | RAM | Speed | Quality | Best For |
|-------|------|-----|-------|---------|----------|
| **Phi-2** | 2.7B | ~5GB | Fast | Excellent | General purpose |
| TinyLlama | 1.1B | ~2GB | Very Fast | Good | Simple tasks |
| Llama-2-7B | 7B | ~14GB | Medium | Very Good | High quality |

## ⚡ Performance Tips

### For CPU-only Systems
```bash
# Use smaller models
huggingface-cli download TinyLlama/TinyLlama-1.1B-Chat-v1.0 --local-dir ./models/tinyllama

# Optimize settings
mcli workflow model-service add-model ./models/tinyllama --name "TinyLlama" --type "text-generation" --device "cpu"
```

### For GPU Systems
```bash
# Use Phi-2 with GPU
mcli workflow model-service add-model ./models/phi-2 --name "Phi-2-GPU" --type "text-generation" --device "cuda"
```

## 🔧 Troubleshooting

### Common Issues
```bash
# Service won't start
mcli workflow model-service stop
mcli workflow model-service start --port 8000

# Model won't load
ls -la ./models/phi-2/  # Check if files exist
mcli workflow model-service status

# Out of memory
mcli workflow model-service update-model MODEL_ID --device "cpu"
mcli workflow model-service remove-model OTHER_MODEL_ID
```

### Check Logs
```bash
# Service logs
tail -f model_service.log

# Health check
curl http://localhost:8000/health
```

## 📊 Monitoring

```bash
# Check service status
mcli workflow model-service status

# Monitor memory usage
curl http://localhost:8000/health

# List models via API
curl http://localhost:8000/models
```

## 🎨 Advanced Usage

### Multiple Model Configurations
```bash
# Creative configuration
mcli workflow model-service add-model ./models/phi-2 --name "Phi-2-Creative" --type "text-generation" --device "auto"
mcli workflow model-service update-model MODEL_ID --temperature 0.9 --max-length 2048

# Conservative configuration
mcli workflow model-service add-model ./models/phi-2 --name "Phi-2-Conservative" --type "text-generation" --device "auto"
mcli workflow model-service update-model MODEL_ID --temperature 0.3 --max-length 512
```

### Python Testing
```python
import requests

# Generate text
response = requests.post(
    "http://localhost:8000/models/MODEL_ID/generate",
    json={"prompt": "Explain machine learning"}
)
print(response.json())

# Classify text
response = requests.post(
    "http://localhost:8000/models/MODEL_ID/classify",
    json={"text": "This is a positive review"}
)
print(response.json())
```

## 📚 Documentation

- **Full Guide**: `cat src/mcli/workflow/model_service/MODEL_MANAGEMENT.md`
- **Setup Script**: `./src/mcli/workflow/model_service/setup_phi2.sh`
- **API Docs**: `curl http://localhost:8000/docs` (when service is running)

## 🆘 Need Help?

1. **Check service status**: `mcli workflow model-service status`
2. **View logs**: `tail -f model_service.log`
3. **Restart service**: `mcli workflow model-service stop && mcli workflow model-service start`
4. **Check health**: `curl http://localhost:8000/health`
5. **Full documentation**: See `MODEL_MANAGEMENT.md`

---

**Quick Start Command**: `./src/mcli/workflow/model_service/setup_phi2.sh` 