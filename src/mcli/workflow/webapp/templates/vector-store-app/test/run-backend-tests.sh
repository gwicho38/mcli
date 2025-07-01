#!/bin/bash

# Backend Integration Test Runner
# Tests all backend functions and API endpoints

set -e

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

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "This script must be run from the vector-store-app directory"
    exit 1
fi

print_status "Starting Backend Integration Tests..."

# Check if Node.js dependencies are installed
if [ ! -d "node_modules" ]; then
    print_warning "Node.js dependencies not found. Installing..."
    npm install
fi

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Python virtual environment not found. Please run install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Python dependencies are installed
print_status "Checking Python dependencies..."
python3 -c "import torch, transformers, sentence_transformers, faiss" 2>/dev/null || {
    print_warning "Python dependencies not found. Installing..."
    cd python && pip install -r requirements.txt && cd ..
}

# Install test dependencies if needed
print_status "Installing test dependencies..."
npm install --save-dev ws form-data

# Create test directories
print_status "Setting up test environment..."
mkdir -p test/test-data
mkdir -p test/test-vector-store

# Run the backend integration tests
print_status "Running backend integration tests..."
node test/backend-integration.test.js

# Check test results
if [ $? -eq 0 ]; then
    print_success "Backend integration tests completed successfully!"
else
    print_error "Backend integration tests failed!"
    exit 1
fi

print_status "Cleaning up test data..."
rm -rf test/test-data/*
rm -rf test/test-vector-store/*

print_success "Backend integration test suite completed!" 