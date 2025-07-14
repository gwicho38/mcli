#!/bin/bash

# MCLI Model Service Installation Script
# This script installs and configures the model service

set -e

echo "🚀 Installing MCLI Model Service..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
check_python() {
    print_status "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Python $PYTHON_VERSION found"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        print_success "Python $PYTHON_VERSION found"
        PYTHON_CMD="python"
    else
        print_error "Python is not installed. Please install Python 3.8+ first."
        exit 1
    fi
    
    # Check Python version
    PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        print_error "Python 3.8+ is required. Found Python $PYTHON_VERSION"
        exit 1
    fi
}

# Check if pip is installed
check_pip() {
    print_status "Checking pip installation..."
    
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        print_error "pip is not installed. Please install pip first."
        exit 1
    fi
    
    print_success "pip found"
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Removing..."
        rm -rf venv
    fi
    
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install core dependencies
    pip install fastapi uvicorn pydantic requests click
    
    # Install machine learning dependencies
    pip install torch transformers accelerate sentencepiece protobuf
    
    # Install data processing dependencies
    pip install numpy Pillow psutil
    
    # Install development dependencies
    pip install pytest pytest-asyncio httpx
    
    print_success "Dependencies installed"
}

# Create configuration
create_config() {
    print_status "Creating configuration..."
    
    cat > config.toml << EOF
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
EOF
    
    print_success "Configuration file created (config.toml)"
}

# Create directories
create_directories() {
    print_status "Creating directories..."
    
    mkdir -p models
    mkdir -p temp
    mkdir -p logs
    
    print_success "Directories created"
}

# Create startup script
create_startup_script() {
    print_status "Creating startup script..."
    
    cat > start_service.sh << 'EOF'
#!/bin/bash

# MCLI Model Service Startup Script

# Activate virtual environment
source venv/bin/activate

# Start the model service
python model_service.py start "$@"
EOF
    
    chmod +x start_service.sh
    print_success "Startup script created (start_service.sh)"
}

# Create systemd service (optional)
create_systemd_service() {
    if command -v systemctl &> /dev/null; then
        print_status "Creating systemd service..."
        
        SERVICE_USER=$(whoami)
        SERVICE_PATH=$(pwd)
        
        sudo tee /etc/systemd/system/mcli-model-service.service > /dev/null << EOF
[Unit]
Description=MCLI Model Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$SERVICE_PATH
ExecStart=$SERVICE_PATH/start_service.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        print_success "Systemd service created"
        print_status "To enable the service, run:"
        echo "  sudo systemctl enable mcli-model-service"
        echo "  sudo systemctl start mcli-model-service"
    else
        print_warning "systemctl not found. Skipping systemd service creation."
    fi
}

# Test installation
test_installation() {
    print_status "Testing installation..."
    
    # Test Python imports
    python -c "import fastapi, uvicorn, torch, transformers" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "All required packages are installed"
    else
        print_error "Some packages are missing. Please check the installation."
        exit 1
    fi
    
    # Test model service
    if [ -f "model_service.py" ]; then
        print_success "Model service script found"
    else
        print_error "Model service script not found"
        exit 1
    fi
}

# Create example usage script
create_example_script() {
    print_status "Creating example usage script..."
    
    cat > example_usage.py << 'EOF'
#!/usr/bin/env python3
"""
Example usage of the MCLI Model Service
"""

import requests
import json

def test_service():
    """Test the model service"""
    base_url = "http://localhost:8000"
    
    try:
        # Check if service is running
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Model service is running")
            print(f"Status: {response.json()}")
        else:
            print("❌ Model service is not responding")
            return
            
        # List models
        response = requests.get(f"{base_url}/models")
        if response.status_code == 200:
            models = response.json()
            print(f"📋 Found {len(models)} models")
            for model in models:
                status = "✅" if model.get('is_loaded') else "⏳"
                print(f"  {status} {model['name']} ({model['model_type']})")
        else:
            print("❌ Failed to list models")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to model service")
        print("Make sure the service is running:")
        print("  python model_service.py start")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_service()
EOF
    
    chmod +x example_usage.py
    print_success "Example usage script created (example_usage.py)"
}

# Main installation function
main() {
    echo "=========================================="
    echo "MCLI Model Service Installation"
    echo "=========================================="
    
    # Check prerequisites
    check_python
    check_pip
    
    # Create environment
    create_venv
    activate_venv
    install_dependencies
    
    # Setup configuration
    create_config
    create_directories
    create_startup_script
    create_systemd_service
    create_example_script
    
    # Test installation
    test_installation
    
    echo ""
    echo "=========================================="
    print_success "Installation completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Start the service:"
    echo "   ./start_service.sh"
    echo ""
    echo "2. Or start with custom options:"
    echo "   python model_service.py start --host 0.0.0.0 --port 8000"
    echo ""
    echo "3. Test the service:"
    echo "   python example_usage.py"
    echo ""
    echo "4. Use the client:"
    echo "   python client.py status"
    echo ""
    echo "5. Load a model:"
    echo "   python client.py load-model gpt2 --name 'GPT-2' --type text-generation"
    echo ""
    echo "Documentation: README.md"
    echo "Configuration: config.toml"
    echo ""
}

# Run installation
main "$@" 