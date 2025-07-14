# Model Management Guide

This guide covers how to download, add, update, and remove models using the MCLI Model Service with `uv` for dependency management.

## Table of Contents
1. [Model Recommendations](#model-recommendations)
2. [Environment Setup with uv](#environment-setup-with-uv)
3. [Downloading Models](#downloading-models)
4. [Adding Models to Service](#adding-models-to-service)
5. [Updating Model Configuration](#updating-model-configuration)
6. [Removing Models](#removing-models)
7. [Testing Models](#testing-models)
8. [Troubleshooting](#troubleshooting)

## Model Recommendations

### Best Overall: Microsoft Phi-2 (2.7B)
- **Size**: 2.7B parameters (~5GB RAM)
- **Performance**: Excellent for its size
- **Speed**: Fast inference
- **Use Cases**: Text generation, classification, translation
- **Download**: `microsoft/phi-2`

### Alternative Options

#### Lightweight (1-3B parameters)
- **TinyLlama-1.1B**: Very fast, good for simple tasks
- **Phi-1.5**: Good balance of size and performance
- **GPT4All-J**: Optimized for CPU inference

#### Medium (3-7B parameters)
- **Llama-2-7B**: Better quality, higher resource usage
- **Mistral-7B**: Excellent performance, more memory
- **CodeLlama-7B**: Specialized for code generation

## Environment Setup with uv

### Install uv (if not already installed)
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

### Using existing MCLI project
The model service is part of the existing MCLI project. All dependencies are already included in the main `pyproject.toml`.

### Install dependencies with uv
```bash
# Install core dependencies (if not already installed)
uv pip install huggingface-hub requests fastapi uvicorn

# Install ML dependencies
uv pip install torch transformers accelerate sentencepiece protobuf

# Install additional utilities
uv pip install numpy pillow psutil python-multipart

# Or install all model-service dependencies at once
uv pip install .[model-service]
```

## Downloading Models

### Method 1: Using huggingface-cli with uv (Recommended)

```bash
# Install huggingface-hub with uv
uv pip install huggingface-hub

# Download Phi-2 (recommended)
huggingface-cli download microsoft/phi-2 --local-dir ./models/phi-2

# Download other models
huggingface-cli download TinyLlama/TinyLlama-1.1B-Chat-v1.0 --local-dir ./models/tinyllama
huggingface-cli download microsoft/DialoGPT-medium --local-dir ./models/dialogpt
```

### Method 2: Using Git LFS

```bash
# Clone with Git LFS
git lfs install
git clone https://huggingface.co/microsoft/phi-2 ./models/phi-2

# For private models, authenticate first
huggingface-cli login
```

### Method 3: Manual Download

```bash
# Create models directory
mkdir -p ./models

# Download from Hugging Face web interface
# 1. Go to https://huggingface.co/microsoft/phi-2
# 2. Click "Files and versions"
# 3. Download individual files or use "Download repository"
# 4. Extract to ./models/phi-2/
```

## Adding Models to Service

### Start the Model Service

```bash
# Start the service
mcli workflow model-service start --host 0.0.0.0 --port 8000 --models-dir ./models

# Check service status
mcli workflow model-service status
```

### Add Phi-2 Model

```bash
# Add Phi-2 for text generation
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2" \
  --type "text-generation" \
  --device "auto"

# Add for text classification
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2-Classifier" \
  --type "text-classification" \
  --device "auto"

# Add for translation
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2-Translator" \
  --type "translation" \
  --device "auto"
```

### Add Other Models

```bash
# Add TinyLlama
mcli workflow model-service add-model ./models/tinyllama \
  --name "TinyLlama" \
  --type "text-generation" \
  --device "cpu"

# Add DialoGPT for conversation
mcli workflow model-service add-model ./models/dialogpt \
  --name "DialoGPT" \
  --type "text-generation" \
  --device "auto"
```

### Verify Model Addition

```bash
# Check service status (shows loaded models)
mcli workflow model-service status

# Check service health via API
curl http://localhost:8000/models
```

## Updating Model Configuration

### Update Model Parameters

```bash
# Update temperature
mcli workflow model-service update-model MODEL_ID \
  --temperature 0.8

# Update multiple parameters
mcli workflow model-service update-model MODEL_ID \
  --temperature 0.8 \
  --max-length 1024 \
  --top-p 0.95 \
  --device "cuda"

# Update model name
mcli workflow model-service update-model MODEL_ID \
  --name "Phi-2-Optimized"
```

### Update via API

```bash
# Using curl
curl -X PUT http://localhost:8000/models/MODEL_ID \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 0.8,
    "max_length": 1024,
    "device": "cuda"
  }'
```

### Verify Updates

```bash
# Check service status to see updated configuration
mcli workflow model-service status

# Or check via API
curl http://localhost:8000/models
```

## Removing Models

### Remove Model from Service

```bash
# Remove with confirmation
mcli workflow model-service remove-model MODEL_ID

# Force remove without confirmation
mcli workflow model-service remove-model MODEL_ID --force
```

### Clean Up Model Files

```bash
# After removing from service, delete model files
rm -rf ./models/phi-2
rm -rf ./models/tinyllama
```

## Testing Models

### Test via API

```bash
# Generate text
curl -X POST http://localhost:8000/models/MODEL_ID/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a short story about a robot learning to paint"
  }'

# Classify text
curl -X POST http://localhost:8000/models/MODEL_ID/classify \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This product is amazing and works perfectly!"
  }'

# Translate text
curl -X POST http://localhost:8000/models/MODEL_ID/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you today?",
    "source_lang": "en",
    "target_lang": "es"
  }'
```

### Test with Python Script

```python
import requests

# Generate text
response = requests.post(
    "http://localhost:8000/models/MODEL_ID/generate",
    json={"prompt": "Explain quantum computing"}
)
print(response.json())

# Classify text
response = requests.post(
    "http://localhost:8000/models/MODEL_ID/classify",
    json={"text": "This is a positive review"}
)
print(response.json())
```

## Complete Workflow Example

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

### 2. Download and Setup Phi-2

```bash
# Download model
huggingface-cli download microsoft/phi-2 --local-dir ./models/phi-2

# Start service
mcli workflow model-service start --port 8000

# Add model
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2" \
  --type "text-generation" \
  --device "auto"
```

### 3. Test and Optimize

```bash
# Test generation via API
curl -X POST http://localhost:8000/models/MODEL_ID/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a Python function to calculate fibonacci numbers"}'

# Update for better performance
mcli workflow model-service update-model MODEL_ID \
  --temperature 0.6 \
  --max-length 1024
```

### 4. Monitor and Maintain

```bash
# Check status
mcli workflow model-service status

# Monitor memory usage via API
curl http://localhost:8000/health
```

## Troubleshooting

### Common Issues

#### Model Won't Load
```bash
# Check model path
ls -la ./models/phi-2/

# Check service logs
mcli workflow model-service status

# Verify model files
find ./models/phi-2/ -name "*.bin" -o -name "*.safetensors"
```

#### Out of Memory
```bash
# Use CPU instead of GPU
mcli workflow model-service update-model MODEL_ID --device "cpu"

# Remove other models
mcli workflow model-service remove-model OTHER_MODEL_ID
```

#### Slow Inference
```bash
# Update to use GPU
mcli workflow model-service update-model MODEL_ID --device "cuda"

# Reduce max_length
mcli workflow model-service update-model MODEL_ID --max-length 512

# Adjust temperature for faster generation
mcli workflow model-service update-model MODEL_ID --temperature 0.3
```

### Performance Optimization

#### For CPU-only Systems
```bash
# Use smaller models
huggingface-cli download TinyLlama/TinyLlama-1.1B-Chat-v1.0 --local-dir ./models/tinyllama

# Optimize for CPU
mcli workflow model-service add-model ./models/tinyllama \
  --name "TinyLlama-CPU" \
  --type "text-generation" \
  --device "cpu"
```

#### For GPU Systems
```bash
# Use larger models with GPU
huggingface-cli download microsoft/phi-2 --local-dir ./models/phi-2

# Optimize for GPU
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2-GPU" \
  --type "text-generation" \
  --device "cuda"
```

### Service Management

```bash
# Stop service
mcli workflow model-service stop

# Start with custom config
mcli workflow model-service start \
  --host 0.0.0.0 \
  --port 8000 \
  --models-dir ./models

# Check service health
mcli workflow model-service status
```

## Model Types Supported

- **text-generation**: For text completion and generation
- **text-classification**: For sentiment analysis and classification
- **translation**: For language translation
- **image-generation**: For image generation (requires additional dependencies)

## Best Practices

1. **Use uv for dependency management**: Ensures reproducible environments
2. **Start Small**: Begin with Phi-2 or TinyLlama for testing
3. **Monitor Resources**: Keep track of memory usage
4. **Use Appropriate Devices**: CPU for small models, GPU for larger ones
5. **Regular Cleanup**: Remove unused models to free space
6. **Backup Configurations**: Save model configurations for reproducibility
7. **Test Thoroughly**: Use API testing for model validation
8. **Document Changes**: Keep track of model updates and configurations

## Advanced Usage

### Custom Model Configurations

```bash
# Create optimized configuration
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2-Creative" \
  --type "text-generation" \
  --device "auto"

# Then update parameters
mcli workflow model-service update-model MODEL_ID \
  --temperature 0.9 \
  --top-p 0.95 \
  --max-length 2048

# Create conservative configuration
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2-Conservative" \
  --type "text-generation" \
  --device "auto"

# Then update parameters
mcli workflow model-service update-model MODEL_ID \
  --temperature 0.3 \
  --top-p 0.8 \
  --max-length 512
```

### Multiple Model Instances

```bash
# Load same model with different configurations
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2-Fast" \
  --type "text-generation" \
  --device "auto"

# Update for fast generation
mcli workflow model-service update-model MODEL_ID \
  --temperature 0.1 \
  --max-length 256

# Load another instance
mcli workflow model-service add-model ./models/phi-2 \
  --name "Phi-2-Creative" \
  --type "text-generation" \
  --device "auto"

# Update for creative generation
mcli workflow model-service update-model MODEL_ID \
  --temperature 0.9 \
  --max-length 1024
```

This guide provides comprehensive coverage of model management with the MCLI Model Service using `uv` for dependency management. Start with Phi-2 for optimal performance and low resource usage, then expand based on your specific needs. 