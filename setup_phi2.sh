#!/bin/bash

# Phi-2 Model Setup Script for MCLI Model Service
# This script downloads and configures Microsoft Phi-2 for optimal performance
# Uses uv for dependency management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MODEL_NAME="microsoft/phi-2"
MODEL_DIR="./models/phi-2"
SERVICE_PORT=8000
SERVICE_HOST="0.0.0.0"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  Phi-2 Model Setup Script${NC}"
echo -e "${BLUE}  Using uv for dependency management${NC}"
echo -e "${BLUE}================================${NC}"

# Check if Python and uv are available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed${NC}"
    echo -e "${YELLOW}💡 Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo -e "${GREEN}✅ uv installed successfully!${NC}"
fi

# Check if we're in the mcli project root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Not in mcli project root. Please run this script from the project root.${NC}"
    exit 1
fi

# Install required packages with uv (using existing project)
echo -e "${YELLOW}📦 Installing required packages with uv...${NC}"
uv pip install huggingface-hub requests fastapi uvicorn
uv pip install torch transformers accelerate sentencepiece protobuf
uv pip install numpy pillow psutil python-multipart

# Create models directory
echo -e "${YELLOW}📁 Creating models directory...${NC}"
mkdir -p "$MODEL_DIR"

# Download Phi-2 model
echo -e "${YELLOW}⬇️  Downloading Phi-2 model (this may take a while)...${NC}"
echo -e "${BLUE}   Model size: ~5GB${NC}"
echo -e "${BLUE}   Estimated time: 5-15 minutes depending on connection${NC}"

if huggingface-cli download "$MODEL_NAME" --local-dir "$MODEL_DIR"; then
    echo -e "${GREEN}✅ Phi-2 model downloaded successfully!${NC}"
else
    echo -e "${RED}❌ Failed to download Phi-2 model${NC}"
    echo -e "${YELLOW}💡 Alternative: Download manually from https://huggingface.co/microsoft/phi-2${NC}"
    exit 1
fi

# Check if model files exist
echo -e "${YELLOW}🔍 Verifying model files...${NC}"
if [ -f "$MODEL_DIR/config.json" ] && [ -f "$MODEL_DIR/pytorch_model.bin" ]; then
    echo -e "${GREEN}✅ Model files verified${NC}"
else
    echo -e "${RED}❌ Model files not found in expected location${NC}"
    echo -e "${YELLOW}💡 Please check the download and try again${NC}"
    exit 1
fi

# Start model service
echo -e "${YELLOW}🚀 Starting model service...${NC}"
echo -e "${BLUE}   Service will be available at http://$SERVICE_HOST:$SERVICE_PORT${NC}"

# Check if service is already running
if curl -s "http://localhost:$SERVICE_PORT/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Model service is already running${NC}"
else
    echo -e "${YELLOW}🔄 Starting model service in background...${NC}"
    nohup mcli workflow model-service start --host "$SERVICE_HOST" --port "$SERVICE_PORT" --models-dir "./models" > model_service.log 2>&1 &
    SERVICE_PID=$!
    echo -e "${BLUE}   Service started with PID: $SERVICE_PID${NC}"
    
    # Wait for service to start
    echo -e "${YELLOW}⏳ Waiting for service to start...${NC}"
    for i in {1..30}; do
        if curl -s "http://localhost:$SERVICE_PORT/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Service is ready!${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ Service failed to start within 30 seconds${NC}"
            echo -e "${YELLOW}💡 Check model_service.log for details${NC}"
            exit 1
        fi
        sleep 1
    done
fi

# Add Phi-2 model to service
echo -e "${YELLOW}📝 Adding Phi-2 model to service...${NC}"

# Add model to service
if mcli workflow model-service add-model "$MODEL_DIR" --name "Phi-2" --type "text-generation" --device "auto"; then
    echo -e "${GREEN}✅ Phi-2 model added successfully!${NC}"
    
    # Get model ID from service status
    MODEL_ID=$(mcli workflow model-service status 2>/dev/null | grep -o 'model_id.*' | cut -d'"' -f3 || echo "")
    if [ -n "$MODEL_ID" ]; then
        echo -e "${BLUE}   Model ID: $MODEL_ID${NC}"
    fi
else
    echo -e "${RED}❌ Failed to add model to service${NC}"
    echo -e "${YELLOW}💡 You can add it manually using:${NC}"
    echo -e "${BLUE}   mcli workflow model-service add-model $MODEL_DIR --name 'Phi-2' --type 'text-generation'${NC}"
fi

# Test the model
echo -e "${YELLOW}🧪 Testing Phi-2 model...${NC}"
if [ -n "$MODEL_ID" ]; then
    TEST_OUTPUT=$(curl -s -X POST "http://localhost:$SERVICE_PORT/models/$MODEL_ID/generate" \
        -H "Content-Type: application/json" \
        -d '{"prompt": "Hello, how are you?"}' 2>/dev/null | grep -o '"generated_text":.*' | cut -d'"' -f4 || echo "")
    if [ -n "$TEST_OUTPUT" ]; then
        echo -e "${GREEN}✅ Model test successful!${NC}"
        echo -e "${BLUE}   Test output: ${TEST_OUTPUT:0:100}...${NC}"
    else
        echo -e "${YELLOW}⚠️  Model test failed, but model may still be working${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Skipping test (no model ID available)${NC}"
fi

# Show final status
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}🎉 Phi-2 Setup Complete!${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}📊 Service Status:${NC}"
mcli workflow model-service status 2>/dev/null || echo "Service status unavailable"

echo -e "${BLUE}📋 Available Commands:${NC}"
echo -e "${GREEN}   Check status:${NC} mcli workflow model-service status"
echo -e "${GREEN}   Generate text:${NC} curl -X POST http://localhost:$SERVICE_PORT/models/MODEL_ID/generate -H 'Content-Type: application/json' -d '{\"prompt\": \"Your prompt here\"}'"
echo -e "${GREEN}   Update model:${NC} mcli workflow model-service update-model MODEL_ID --temperature 0.8"
echo -e "${GREEN}   Remove model:${NC} mcli workflow model-service remove-model MODEL_ID"

echo -e "${BLUE}📚 Documentation:${NC}"
echo -e "${GREEN}   Full guide:${NC} cat src/mcli/workflow/model_service/MODEL_MANAGEMENT.md"

echo -e "${BLUE}🔧 Troubleshooting:${NC}"
echo -e "${GREEN}   Check logs:${NC} tail -f model_service.log"
echo -e "${GREEN}   Restart service:${NC} mcli workflow model-service stop && mcli workflow model-service start"
echo -e "${GREEN}   Check health:${NC} curl http://localhost:$SERVICE_PORT/health"

echo -e "${BLUE}🌱 uv Environment:${NC}"
echo -e "${GREEN}   Install dependencies:${NC} uv pip install package-name"
echo -e "${GREEN}   Install model-service extras:${NC} uv pip install .[model-service]"

echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}🚀 Your Phi-2 model is ready to use!${NC}"
echo -e "${BLUE}================================${NC}" 