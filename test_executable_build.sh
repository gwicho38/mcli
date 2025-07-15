#!/bin/bash

# Test script for building executable from wheel
echo "Testing executable build from wheel..."
echo "Date: $(date)"
echo "Directory: $(pwd)"
echo "-------------------------------------------"

# Clean any previous build artifacts
echo "Cleaning previous build artifacts..."
make clean

# Setup the environment
echo "Setting up environment..."
make setup

# Build the wheel
echo "Building wheel..."
make wheel

# Build portable executable
echo "Building portable executable..."
make portable

# Test the executable
echo "Testing the executable..."
make test-binary

# Show the results
echo "-------------------------------------------"
echo "Build Results:"
echo "Wheel files:"
ls -la dist/ 2>/dev/null || echo "No wheel files found"

echo "Executable files:"
ls -la bin/ 2>/dev/null || echo "No executable files found"

echo "-------------------------------------------"
echo "To install the executable system-wide, run:"
echo "  make install-portable"
echo ""
echo "To test the executable, run:"
echo "  make test-binary"
echo ""
echo "To clean everything, run:"
echo "  make clean" 