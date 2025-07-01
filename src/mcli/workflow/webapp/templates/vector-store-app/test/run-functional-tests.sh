#!/bin/bash

# Functional Test Runner for Vector Store Manager
# Tests actual vector operations, database creation, and document processing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$TEST_DIR")"
REPORT_DIR="$TEST_DIR/test-reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create report directory
mkdir -p "$REPORT_DIR"

echo -e "${BLUE}🔍 Vector Store Manager - Functional Test Suite${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed or not in PATH"
    exit 1
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed or not in PATH"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

print_success "Prerequisites check passed"

# Install dependencies if needed
print_status "Installing test dependencies..."
cd "$TEST_DIR"

if [ ! -d "node_modules" ]; then
    npm install
    print_success "Test dependencies installed"
else
    print_success "Test dependencies already installed"
fi

# Install Playwright browsers if needed
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    print_status "Installing Playwright browsers..."
    npx playwright install
    print_success "Playwright browsers installed"
else
    print_success "Playwright browsers already installed"
fi

# Check if app dependencies are installed
cd "$APP_DIR"
if [ ! -d "node_modules" ]; then
    print_status "Installing app dependencies..."
    npm install --no-optional
    print_success "App dependencies installed"
else
    print_success "App dependencies already installed"
fi

# Return to test directory
cd "$TEST_DIR"

# Clean up any existing processes
print_status "Cleaning up existing processes..."
pkill -f "Electron" || true
pkill -f "python.*generate_embeddings" || true
sleep 2

# Run functional tests
print_status "Running functional tests..."
echo ""

# Run the functional test suite
TEST_RESULT=0
npx playwright test functional-vectorstore.test.js \
    --timeout=180000 \
    --reporter=html \
    --output-dir="$REPORT_DIR/functional-$TIMESTAMP" || TEST_RESULT=$?

echo ""

# Check test results
if [ $TEST_RESULT -eq 0 ]; then
    print_success "All functional tests passed!"
    echo ""
    echo -e "${GREEN}🎉 Vector Store functional validation complete!${NC}"
    echo ""
    echo "Test coverage:"
    echo "  ✅ Vector database creation and storage"
    echo "  ✅ Document embedding generation"
    echo "  ✅ Semantic search functionality"
    echo "  ✅ Exact match search"
    echo "  ✅ UI state synchronization"
    echo "  ✅ Document CRUD operations"
    echo "  ✅ Vector visualization generation"
    echo "  ✅ WebSocket real-time communication"
    echo "  ✅ Data persistence across restarts"
    echo ""
else
    print_error "Some functional tests failed!"
    echo ""
    echo -e "${RED}🔍 Check the test report for details:${NC}"
    echo "  $REPORT_DIR/functional-$TIMESTAMP/index.html"
    echo ""
    echo "Common issues:"
    echo "  - Python dependencies not installed (torch, sentence-transformers)"
    echo "  - Port conflicts (should be handled automatically)"
    echo "  - Insufficient memory for embedding generation"
    echo "  - File permission issues"
    echo ""
fi

# Generate summary report
REPORT_FILE="$REPORT_DIR/functional-summary-$TIMESTAMP.json"
cat > "$REPORT_FILE" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "test_suite": "functional-vectorstore",
  "status": "$([ $TEST_RESULT -eq 0 ] && echo "PASS" || echo "FAIL")",
  "exit_code": $TEST_RESULT,
  "test_coverage": {
    "vector_database": "Database creation and document storage",
    "embeddings": "Text embedding generation and storage",
    "semantic_search": "AI-powered semantic search",
    "exact_search": "Exact text matching",
    "ui_sync": "UI state synchronization",
    "crud_operations": "Document create, read, update, delete",
    "visualization": "Vector space visualization",
    "websocket": "Real-time WebSocket communication",
    "persistence": "Data persistence across app restarts"
  },
  "environment": {
    "node_version": "$(node --version)",
    "npm_version": "$(npm --version)",
    "python_version": "$(python3 --version)",
    "platform": "$(uname -s)",
    "architecture": "$(uname -m)"
  }
}
EOF

print_status "Test summary saved to: $REPORT_FILE"

# Show report location
if [ $TEST_RESULT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}📊 Test Report:${NC}"
    echo "  $REPORT_DIR/functional-$TIMESTAMP/index.html"
    echo ""
    echo -e "${GREEN}📋 Summary:${NC}"
    echo "  $REPORT_FILE"
    echo ""
    echo -e "${GREEN}🚀 Vector Store Manager is ready for production!${NC}"
else
    echo ""
    echo -e "${RED}📊 Test Report:${NC}"
    echo "  $REPORT_DIR/functional-$TIMESTAMP/index.html"
    echo ""
    echo -e "${RED}📋 Summary:${NC}"
    echo "  $REPORT_FILE"
    echo ""
    echo -e "${RED}🔧 Please fix the failing tests before deployment${NC}"
fi

exit $TEST_RESULT 