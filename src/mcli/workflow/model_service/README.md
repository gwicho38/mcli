# MCLI Model Service

A powerful daemon service for hosting and providing inference APIs for arbitrary language models. The service runs as a background daemon and provides a REST API for model management and inference.

## Features

### 🚀 **Multi-Model Support**

- **Text Generation**: GPT-style models for text completion and generation
- **Text Classification**: BERT-style models for sentiment analysis and classification
- **Translation**: Sequence-to-sequence models for language translation
- **Image Generation**: Support for diffusion models (planned)
- **Custom Models**: Extensible architecture for custom model types

### 🎯 **Easy Model Management**

- **Dynamic Loading**: Load and unload models without restarting the service
- **Model Caching**: Intelligent caching with configurable memory limits
- **Metadata Storage**: SQLite database for model metadata and inference history
- **Device Management**: Automatic GPU/CPU detection and management

### 🌐 **REST API**

- **FastAPI**: Modern, fast web framework with automatic documentation
- **CORS Support**: Cross-origin resource sharing for web applications
- **Health Checks**: Built-in health monitoring endpoints
- **Error Handling**: Comprehensive error handling and reporting

### 📊 **Monitoring & Analytics**

- **Inference History**: Track all inference requests and responses
- **Performance Metrics**: Execution time and memory usage tracking
- **Error Logging**: Detailed error logging and debugging information
- **Resource Monitoring**: Real-time resource usage monitoring

## Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Electron      │    │   Web Client    │    │   CLI Client    │
│   Frontend      │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │    Model Service API      │
                    │    (FastAPI + Uvicorn)   │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     Model Manager         │
                    │  (Loading & Caching)     │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │   Model Database          │
                    │     (SQLite)              │
                    └───────────────────────────┘
```

## Installation

### Prerequisites

1. **Python 3.8+**: The service requires Python 3.8 or higher
2. **PyTorch**: Install PyTorch for your system (CPU or CUDA)
3. **Transformers**: Install the Hugging Face Transformers library

### Quick Start

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Start the service**:

   ```bash
   python model_service.py start
   ```

3. **Check status**:

   ```bash
   python model_service.py status
   ```

## Usage

### Starting the Service

```bash
# Start with default settings
python model_service.py start

# Start with custom configuration
python model_service.py start --host 0.0.0.0 --port 8000 --models-dir ./models

# Start with config file
python model_service.py start --config config.toml
```

### Using the Client

```bash
# Check service status
python client.py status

# List available models
python client.py list-models

# Load a model
python client.py load-model /path/to/model --name "My Model" --type text-generation

# Update a model
python client.py update-model <model_id> --name "New Name" --temperature 0.8

# Remove a model
python client.py remove-model <model_id>

# Generate text
python client.py generate <model_id> "Hello, how are you?"

# Test a model
python client.py test-model --model-id <model_id> --prompt "Test prompt"
```

### API Endpoints

#### Service Information

- `GET /` - Service status and information
- `GET /health` - Health check with resource usage

#### Model Management

- `GET /models` - List all available models
- `POST /models` - Load a new model
- `PUT /models/{model_id}` - Update model configuration
- `DELETE /models/{model_id}` - Unload a model
- `DELETE /models/{model_id}/remove` - Remove a model from database

#### Inference

- `POST /models/{model_id}/generate` - Generate text
- `POST /models/{model_id}/classify` - Classify text
- `POST /models/{model_id}/translate` - Translate text

## Configuration

### Environment Variables

- `MODEL_SERVICE_HOST` - Host to bind to (default: 0.0.0.0)
- `MODEL_SERVICE_PORT` - Port to bind to (default: 8000)
- `MODEL_SERVICE_MODELS_DIR` - Directory for model storage
- `MODEL_SERVICE_MAX_CACHE_SIZE` - Maximum number of models to cache

### Configuration File

Create a `config.toml` file:

```toml
[model_service]
host = "0.0.0.0"
port = 8000
models_dir = "./models"
temp_dir = "./temp"
max_concurrent_requests = 4
request_timeout = 300
model_cache_size = 2
enable_cors = true
cors_origins = ["*"]
log_level = "INFO"
```

## Model Types

### Text Generation Models

Supported formats:

- Hugging Face Transformers models
- Custom PyTorch models
- ONNX models (planned)

Example usage:

```python
# Load a text generation model
model_id = client.load_model(
    name="GPT-2 Small",
    model_type="text-generation",
    model_path="gpt2",
    temperature=0.7,
    max_length=100
)

# Generate text
result = client.generate_text(model_id, "Hello, how are you?")
print(result['generated_text'])
```

### Text Classification Models

Example usage:

```python
# Load a classification model
model_id = client.load_model(
    name="BERT Sentiment",
    model_type="text-classification",
    model_path="nlptown/bert-base-multilingual-uncased-sentiment"
)

# Classify text
result = client.classify_text(model_id, "I love this product!")
print(result['classifications'])
```

### Translation Models

Example usage:

```python
# Load a translation model
model_id = client.load_model(
    name="Marian EN-FR",
    model_type="translation",
    model_path="Helsinki-NLP/opus-mt-en-fr"
)

# Translate text
result = client.translate_text(
    model_id, 
    "Hello, how are you?", 
    source_lang="en", 
    target_lang="fr"
)
print(result['translated_text'])
```

## Integration with Electron Frontend

The model service is designed to work seamlessly with Electron applications. Here's an example of how to integrate it:

### JavaScript/TypeScript Client

```typescript
class ModelServiceClient {
    private baseUrl: string;

    constructor(baseUrl: string = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    async generateText(modelId: string, prompt: string): Promise<string> {
        const response = await fetch(`${this.baseUrl}/models/${modelId}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result.generated_text;
    }

    async listModels(): Promise<any[]> {
        const response = await fetch(`${this.baseUrl}/models`);
        return await response.json();
    }
}

// Usage in Electron
const modelClient = new ModelServiceClient();
const models = await modelClient.listModels();
const generatedText = await modelClient.generateText(modelId, "Hello, world!");
```

### Python Integration

```python
import requests

class ElectronModelClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def generate_text(self, model_id: str, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/models/{model_id}/generate",
            json={"prompt": prompt}
        )
        response.raise_for_status()
        return response.json()["generated_text"]

# Usage in Electron with Python bridge
import subprocess

def call_model_service(model_id: str, prompt: str) -> str:
    result = subprocess.run([
        "python", "client.py", "generate", model_id, prompt
    ], capture_output=True, text=True)
    return result.stdout
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_model_service.py

# Run with coverage
pytest --cov=model_service tests/
```

### Adding New Model Types

To add support for new model types:

1. **Extend ModelManager**:

   ```python
   def _load_custom_model(self, model_info: ModelInfo):
       # Custom loading logic
       pass
   ```

2. **Add inference method**:

   ```python
   def custom_inference(self, model_id: str, input_data: Any) -> Any:
       # Custom inference logic
       pass
   ```

3. **Add API endpoint**:

   ```python
   @self.app.post("/models/{model_id}/custom")
   async def custom_inference(model_id: str, request: CustomRequest):
       # API endpoint logic
       pass
   ```

## Troubleshooting

### Common Issues

1. **Model loading fails**:
   - Check if the model path is correct
   - Ensure you have enough disk space
   - Verify model format compatibility

2. **Out of memory errors**:
   - Reduce `model_cache_size` in configuration
   - Use CPU instead of GPU for large models
   - Unload unused models

3. **API connection errors**:
   - Check if the service is running
   - Verify the correct port and host
   - Check firewall settings

### Logs

The service logs are stored in:

- System logs: `/var/log/mcli/model_service.log`
- User logs: `~/.local/mcli/model_service/logs/`

### Performance Tuning

1. **Memory optimization**:
   - Use model quantization (INT8/FP16)
   - Enable gradient checkpointing
   - Use model sharding for large models

2. **Speed optimization**:
   - Use GPU acceleration
   - Enable model caching
   - Use batch processing

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Join the community discussions
