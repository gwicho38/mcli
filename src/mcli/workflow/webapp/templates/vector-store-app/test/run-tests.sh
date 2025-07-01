#!/bin/bash

# Vector Store Manager - Puppeteer Test Runner
# This script runs comprehensive tests for the Vector Store Manager application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Node.js version
check_node_version() {
    if ! command_exists node; then
        print_error "Node.js is not installed"
        exit 1
    fi
    
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 16 ]; then
        print_error "Node.js version 16 or higher is required. Found: $(node --version)"
        exit 1
    fi
    
    print_success "Node.js version: $(node --version)"
}

# Function to check if app is running
check_app_running() {
    if lsof -ti:3001 >/dev/null 2>&1; then
        print_warning "App is already running on port 3001"
        read -p "Do you want to stop it and continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            lsof -ti:3001 | xargs kill -9
            sleep 2
        else
            print_error "Please stop the app manually and try again"
            exit 1
        fi
    fi
}

# Function to install test dependencies
install_test_dependencies() {
    print_info "Installing test dependencies..."
    
    cd "$(dirname "$0")"
    
    if [ ! -f "package.json" ]; then
        print_error "package.json not found in test directory"
        exit 1
    fi
    
    if [ ! -d "node_modules" ]; then
        print_info "Installing npm dependencies..."
        npm install
    else
        print_info "Dependencies already installed"
    fi
}

# Function to run basic tests
run_basic_tests() {
    print_info "Running basic Puppeteer tests..."
    
    cd "$(dirname "$0")"
    
    if node puppeteer-test.js; then
        print_success "Basic tests completed successfully"
        return 0
    else
        print_error "Basic tests failed"
        return 1
    fi
}

# Function to run advanced tests
run_advanced_tests() {
    print_info "Running advanced Puppeteer tests..."
    
    cd "$(dirname "$0")"
    
    if node advanced-test-suite.js; then
        print_success "Advanced tests completed successfully"
        return 0
    else
        print_error "Advanced tests failed"
        return 1
    fi
}

# Function to run specific test
run_specific_test() {
    local test_name="$1"
    print_info "Running specific test: $test_name"
    
    cd "$(dirname "$0")"
    
    case "$test_name" in
        "basic"|"simple")
            run_basic_tests
            ;;
        "advanced"|"full")
            run_advanced_tests
            ;;
        "api")
            print_info "Running API endpoint tests..."
            node -e "
                const tester = require('./advanced-test-suite');
                const test = new tester();
                test.startApp().then(() => {
                    return test.testAPIEndpoints();
                }).then(() => {
                    console.log('API tests passed');
                    process.exit(0);
                }).catch((error) => {
                    console.error('API tests failed:', error);
                    process.exit(1);
                });
            "
            ;;
        "ui")
            print_info "Running UI interaction tests..."
            node -e "
                const tester = require('./puppeteer-test');
                const test = new tester();
                test.startApp().then(() => {
                    return test.connectToApp();
                }).then(() => {
                    return test.testAppLoading();
                }).then(() => {
                    console.log('UI tests passed');
                    process.exit(0);
                }).catch((error) => {
                    console.error('UI tests failed:', error);
                    process.exit(1);
                });
            "
            ;;
        *)
            print_error "Unknown test type: $test_name"
            print_info "Available tests: basic, advanced, api, ui"
            exit 1
            ;;
    esac
}

# Function to generate test report
generate_test_report() {
    print_info "Generating test report..."
    
    cd "$(dirname "$0")"
    
    local report_file="test-report-$(date +%Y%m%d-%H%M%S).json"
    
    # Run tests and capture output
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        echo "  \"app_version\": \"$(node -p "require('../package.json').version")\","
        echo "  \"node_version\": \"$(node --version)\","
        echo "  \"tests\": {"
        
        # Run basic tests
        echo "    \"basic\": {"
        if run_basic_tests >/dev/null 2>&1; then
            echo "      \"status\": \"PASS\","
            echo "      \"message\": \"Basic tests completed successfully\""
        else
            echo "      \"status\": \"FAIL\","
            echo "      \"message\": \"Basic tests failed\""
        fi
        echo "    },"
        
        # Run advanced tests
        echo "    \"advanced\": {"
        if run_advanced_tests >/dev/null 2>&1; then
            echo "      \"status\": \"PASS\","
            echo "      \"message\": \"Advanced tests completed successfully\""
        else
            echo "      \"status\": \"FAIL\","
            echo "      \"message\": \"Advanced tests failed\""
        fi
        echo "    }"
        
        echo "  }"
        echo "}"
    } > "$report_file"
    
    print_success "Test report generated: $report_file"
}

# Function to show help
show_help() {
    echo "Vector Store Manager - Puppeteer Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS] [TEST_TYPE]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -r, --report        Generate test report"
    echo "  -c, --check         Check environment only"
    echo "  -v, --verbose       Verbose output"
    echo ""
    echo "Test Types:"
    echo "  basic               Run basic Puppeteer tests"
    echo "  advanced            Run advanced test suite"
    echo "  api                 Run API endpoint tests only"
    echo "  ui                  Run UI interaction tests only"
    echo "  all                 Run all tests (default)"
    echo ""
    echo "Examples:"
    echo "  $0                  Run all tests"
    echo "  $0 basic            Run basic tests only"
    echo "  $0 --report         Generate test report"
    echo "  $0 --check          Check environment only"
}

# Main execution
main() {
    local test_type="all"
    local generate_report=false
    local check_only=false
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -r|--report)
                generate_report=true
                shift
                ;;
            -c|--check)
                check_only=true
                shift
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            basic|advanced|api|ui|all)
                test_type="$1"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_info "Vector Store Manager - Puppeteer Test Runner"
    print_info "Test type: $test_type"
    
    # Check environment
    check_node_version
    check_app_running
    
    if [ "$check_only" = true ]; then
        print_success "Environment check completed"
        exit 0
    fi
    
    # Install dependencies
    install_test_dependencies
    
    # Run tests based on type
    case "$test_type" in
        "all")
            print_info "Running all tests..."
            run_basic_tests
            run_advanced_tests
            ;;
        "basic")
            run_basic_tests
            ;;
        "advanced")
            run_advanced_tests
            ;;
        *)
            run_specific_test "$test_type"
            ;;
    esac
    
    # Generate report if requested
    if [ "$generate_report" = true ]; then
        generate_test_report
    fi
    
    print_success "Test execution completed"
}

# Run main function with all arguments
main "$@" 