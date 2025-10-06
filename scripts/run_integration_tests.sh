#!/bin/bash
# run_integration_tests.sh - Run End-to-End Integration Tests
#
# This script runs comprehensive integration tests that verify:
# - Streamlit Dashboard functionality
# - LSH Daemon connectivity and API
# - Supabase database integration
# - Complete data flow and ML prediction pipeline
#
# Usage:
#   ./scripts/run_integration_tests.sh [options]
#
# Options:
#   --quick       Run only connectivity tests (fast)
#   --full        Run all integration tests (default)
#   --verbose     Show detailed output
#   --coverage    Generate coverage report
#   --help        Show this help message

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default options
TEST_MODE="full"
VERBOSE=false
COVERAGE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            TEST_MODE="quick"
            shift
            ;;
        --full)
            TEST_MODE="full"
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --quick       Run only connectivity tests (fast)"
            echo "  --full        Run all integration tests (default)"
            echo "  --verbose     Show detailed output"
            echo "  --coverage    Generate coverage report"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Python
    if ! command -v python &> /dev/null; then
        print_error "Python not found"
        exit 1
    fi
    print_success "Python: $(python --version)"

    # Check pytest
    if ! python -c "import pytest" 2>/dev/null; then
        print_warning "pytest not installed, installing..."
        pip install pytest pytest-asyncio
    fi
    print_success "pytest installed"

    # Check required packages
    if ! python -c "import requests" 2>/dev/null; then
        print_warning "requests not installed, installing..."
        pip install requests
    fi
    print_success "requests installed"

    if ! python -c "import supabase" 2>/dev/null; then
        print_warning "supabase not installed, installing..."
        pip install supabase
    fi
    print_success "supabase installed"

    # Check environment variables
    if [ -z "$SUPABASE_URL" ]; then
        print_warning "SUPABASE_URL not set, loading from .env"
        export $(grep -v '^#' .env | xargs)
    fi

    if [ -z "$LSH_API_URL" ]; then
        print_warning "LSH_API_URL not set, using default"
        export LSH_API_URL="https://mcli-lsh-daemon.fly.dev"
    fi

    print_success "Environment configured"
}

# Run tests
run_tests() {
    print_header "Running Integration Tests"

    TEST_FILE="tests/integration/test_e2e_dashboard_lsh_supabase.py"

    if [ ! -f "$TEST_FILE" ]; then
        print_error "Test file not found: $TEST_FILE"
        exit 1
    fi

    # Build pytest command
    PYTEST_CMD=".venv/bin/pytest"

    # Check if virtual environment exists
    if [ ! -f "$PYTEST_CMD" ]; then
        print_warning "Virtual environment not found, using system pytest"
        PYTEST_CMD="pytest"
    fi

    PYTEST_ARGS="$TEST_FILE"

    # Add verbose flag if requested
    if [ "$VERBOSE" = true ]; then
        PYTEST_ARGS="$PYTEST_ARGS -v -s"
    else
        PYTEST_ARGS="$PYTEST_ARGS -v"
    fi

    # Add coverage if requested
    if [ "$COVERAGE" = true ]; then
        PYTEST_ARGS="$PYTEST_ARGS --cov=src/mcli --cov-report=html --cov-report=term"
    fi

    # Select test mode
    if [ "$TEST_MODE" = "quick" ]; then
        print_info "Running quick tests (connectivity only)..."
        PYTEST_ARGS="$PYTEST_ARGS -k TestInfrastructureConnectivity"
    else
        print_info "Running full integration test suite..."
    fi

    # Run tests
    print_info "Command: $PYTEST_CMD $PYTEST_ARGS"
    echo ""

    if $PYTEST_CMD $PYTEST_ARGS; then
        print_success "All tests passed!"
        return 0
    else
        print_error "Some tests failed"
        return 1
    fi
}

# Show test summary
show_summary() {
    print_header "Test Summary"

    echo -e "${BLUE}Integration tests completed${NC}"
    echo ""
    echo "Tested components:"
    echo "  ✓ LSH Daemon (https://mcli-lsh-daemon.fly.dev)"
    echo "  ✓ Supabase Database"
    echo "  ✓ ML Prediction Pipeline"
    echo "  ✓ Data Flow (Supabase ↔ Dashboard ↔ LSH)"
    echo ""

    if [ "$COVERAGE" = true ]; then
        print_info "Coverage report generated: htmlcov/index.html"
    fi

    echo ""
}

# Main execution
main() {
    print_header "E2E Integration Tests: Dashboard ↔ LSH ↔ Supabase"

    check_prerequisites

    if run_tests; then
        show_summary
        exit 0
    else
        print_error "Tests failed - see output above"
        exit 1
    fi
}

# Run main function
main
