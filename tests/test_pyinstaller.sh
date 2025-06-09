#!/bin/bash

# Test script for PyInstaller build
echo "Testing PyInstaller build..."
echo "Date: $(date)"
echo "Directory: $(pwd)"
echo "-------------------------------------------"

# Create required directories
mkdir -p db dependencies src/mcli/private src/mcli/public
touch db/.gitkeep dependencies/.gitkeep

# Clean any previous build artifacts
echo "Cleaning previous build artifacts..."
make clean

# Run the portable target and capture the output
echo "Running the portable target..."
make portable > pyinstaller_build.log 2>&1
BUILD_RESULT=$?

# Check the result
if [ $BUILD_RESULT -eq 0 ]; then
    echo "Build completed successfully!"
    echo "Testing the binary..."
    make test-binary
    TEST_RESULT=$?
    
    if [ $TEST_RESULT -eq 0 ]; then
        echo "Binary test completed successfully!"
        echo "OVERALL RESULT: SUCCESS ✅"
        exit 0
    else
        echo "Binary test failed with exit code: $TEST_RESULT"
        echo "See pyinstaller_build.log for details"
        echo "OVERALL RESULT: BINARY TEST FAILED ❌"
        exit 1
    fi
else
    echo "Build failed with exit code: $BUILD_RESULT"
    echo "See pyinstaller_build.log for details"
    echo "OVERALL RESULT: BUILD FAILED ❌"
    exit 1
fi