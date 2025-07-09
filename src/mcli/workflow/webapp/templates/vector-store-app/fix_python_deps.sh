#!/bin/bash

# Fix Python Dependencies for Vector Store Manager
# This script ensures all Python dependencies are properly installed

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "This script must be run from the vector-store-app directory"
    exit 1
fi

print_status "Fixing Python dependencies for Vector Store Manager..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1)
print_success "Using Python: $PYTHON_VERSION"

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ -f "python/requirements_minimal.txt" ]; then
    cd python
    
    # Install torch first (it can be tricky)
    print_status "Installing PyTorch..."
    pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
    
    # Install other dependencies
    print_status "Installing other dependencies..."
    pip install -r requirements_minimal.txt
    
    cd ..
    print_success "Python dependencies installed"
elif [ -f "python/requirements.txt" ]; then
    cd python
    
    # Install torch first (it can be tricky)
    print_status "Installing PyTorch..."
    pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
    
    # Install other dependencies
    print_status "Installing other dependencies..."
    pip install -r requirements.txt
    
    cd ..
    print_success "Python dependencies installed"
else
    print_error "No requirements file found"
    exit 1
fi

# Test if torch is available
print_status "Testing torch installation..."
python -c "import torch; print(f'PyTorch version: {torch.__version__}')" || {
    print_error "Torch installation failed"
    exit 1
}

# Test other critical dependencies
print_status "Testing critical dependencies..."
python -c "
import sentence_transformers
import transformers
import numpy
import faiss
print('All critical dependencies are available')
" || {
    print_error "Some critical dependencies are missing"
    exit 1
}

print_success "Python dependencies fixed successfully!"
print_status "You can now run the Vector Store Manager with: npm start" 