#!/bin/bash

# Test Workflow for Phi-2 Model Management
# This script demonstrates the complete workflow for managing Phi-2
# Uses uv for dependency management

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  Phi-2 Model Workflow Test${NC}"
echo -e "${BLUE}  Using uv for dependency management${NC}"
echo -e "${BLUE}================================${NC}"

# Step 1: Check if we're in the mcli project root
echo -e "${YELLOW}Step 1: Checking project structure...${NC}"
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Not in mcli project root. Please run this script from the project root.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Found existing mcli project${NC}"

# Install dependencies with uv (using existing project)
echo -e "${BLUE}Installing dependencies with uv...${NC}"
uv pip install huggingface-hub requests fastapi uvicorn
uv pip install torch transformers accelerate sentencepiece protobuf
uv pip install numpy pillow psutil python-multipart
echo -e "${GREEN}✅ Dependencies installed!${NC}"

# Step 2: Download Phi-2 (if not already downloaded)
echo -e "${YELLOW}Step 2: Downloading Phi-2 model...${NC}"
if [ ! -d "./models/phi-2" ]; then
    echo -e "${BLUE}Downloading Phi-2 (this may take a while)...${NC}"
    huggingface-cli download microsoft/phi-2 --local-dir ./models/phi-2
    echo -e "${GREEN}✅ Phi-2 downloaded successfully!${NC}"
else
    echo -e "${GREEN}✅ Phi-2 already exists in ./models/phi-2${NC}"
fi

# Step 3: Start the model service
echo -e "${YELLOW}Step 3: Starting model service...${NC}"
mcli workflow model-service start --port 8000 &
SERVICE_PID=$!
echo -e "${BLUE}Service started with PID: $SERVICE_PID${NC}"

# Wait for service to start
echo -e "${YELLOW}Waiting for service to start...${NC}"
sleep 5

# Step 4: Add Phi-2 model
echo -e "${YELLOW}Step 4: Adding Phi-2 model to service...${NC}"
mcli workflow model-service add-model ./models/phi-2 --name "Phi-2" --type "text-generation" --device "auto"
echo -e "${GREEN}✅ Phi-2 model added successfully!${NC}"

# Step 5: Check service status
echo -e "${YELLOW}Step 5: Checking service status...${NC}"
mcli workflow model-service status

# Step 6: Test model via API
echo -e "${YELLOW}Step 6: Testing model via API...${NC}"
echo -e "${BLUE}Testing text generation...${NC}"

# Get model ID from service
MODEL_ID=$(curl -s http://localhost:8000/models | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$MODEL_ID" ]; then
    echo -e "${BLUE}Model ID: $MODEL_ID${NC}"
    
    # Test generation
    RESPONSE=$(curl -s -X POST "http://localhost:8000/models/$MODEL_ID/generate" \
        -H "Content-Type: application/json" \
        -d '{"prompt": "Hello, how are you?"}')
    
    echo -e "${GREEN}✅ API test successful!${NC}"
    echo -e "${BLUE}Response: $RESPONSE${NC}"
else
    echo -e "${RED}❌ Could not get model ID${NC}"
fi

# Step 7: Update model configuration
echo -e "${YELLOW}Step 7: Updating model configuration...${NC}"
if [ -n "$MODEL_ID" ]; then
    mcli workflow model-service update-model "$MODEL_ID" --temperature 0.8 --max-length 1024
    echo -e "${GREEN}✅ Model configuration updated!${NC}"
fi

# Step 8: Test updated model
echo -e "${YELLOW}Step 8: Testing updated model...${NC}"
if [ -n "$MODEL_ID" ]; then
    RESPONSE=$(curl -s -X POST "http://localhost:8000/models/$MODEL_ID/generate" \
        -H "Content-Type: application/json" \
        -d '{"prompt": "Write a short poem about AI"}')
    
    echo -e "${GREEN}✅ Updated model test successful!${NC}"
    echo -e "${BLUE}Response: $RESPONSE${NC}"
fi

# Step 9: Show final status
echo -e "${YELLOW}Step 9: Final service status...${NC}"
mcli workflow model-service status

# Step 10: Cleanup (optional)
echo -e "${YELLOW}Step 10: Cleanup options...${NC}"
echo -e "${BLUE}To remove the model:${NC}"
echo -e "${GREEN}   mcli workflow model-service remove-model $MODEL_ID${NC}"
echo -e "${BLUE}To stop the service:${NC}"
echo -e "${GREEN}   mcli workflow model-service stop${NC}"

echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}🎉 Phi-2 workflow test complete!${NC}"
echo -e "${BLUE}================================${NC}"

# Keep service running for manual testing
echo -e "${YELLOW}Service is still running for manual testing.${NC}"
echo -e "${BLUE}Test commands:${NC}"
echo -e "${GREEN}   Check status:${NC} mcli workflow model-service status"
echo -e "${GREEN}   Generate text:${NC} curl -X POST http://localhost:8000/models/$MODEL_ID/generate -H 'Content-Type: application/json' -d '{\"prompt\": \"Your prompt here\"}'"
echo -e "${GREEN}   Stop service:${NC} mcli workflow model-service stop"

echo -e "${BLUE}🌱 uv Environment Info:${NC}"
echo -e "${GREEN}   Install dependencies:${NC} uv pip install package-name"
echo -e "${GREEN}   Install model-service extras:${NC} uv pip install .[model-service]" 