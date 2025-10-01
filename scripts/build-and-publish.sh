#!/bin/bash
set -e

# MCLI Build and Publish Script
# Comprehensive build, test, and publish workflow

VERSION="1.0.0"
SCRIPT_NAME="$(basename "$0")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Functions
print_header() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════╗"
    echo "║     MCLI Build & Publish Workflow        ║"
    echo "║          Version ${VERSION}                    ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Main build workflow
main() {
    print_header

    # Parse arguments
    BUILD_TYPE="full"  # full, wheel, binary
    RUN_TESTS="true"
    PUBLISH="false"
    PUBLISH_TEST="false"
    VALIDATE="true"

    while [[ $# -gt 0 ]]; do
        case $1 in
            --wheel)
                BUILD_TYPE="wheel"
                shift
                ;;
            --binary)
                BUILD_TYPE="binary"
                shift
                ;;
            --full)
                BUILD_TYPE="full"
                shift
                ;;
            --no-tests)
                RUN_TESTS="false"
                shift
                ;;
            --no-validate)
                VALIDATE="false"
                shift
                ;;
            --publish)
                PUBLISH="true"
                shift
                ;;
            --publish-test)
                PUBLISH_TEST="true"
                shift
                ;;
            --help|-h)
                echo "Usage: $SCRIPT_NAME [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --wheel         Build wheel only"
                echo "  --binary        Build binary only"
                echo "  --full          Build all targets (default)"
                echo "  --no-tests      Skip testing"
                echo "  --no-validate   Skip validation"
                echo "  --publish       Publish to PyPI"
                echo "  --publish-test  Publish to Test PyPI"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Run '$SCRIPT_NAME --help' for usage"
                exit 1
                ;;
        esac
    done

    # Clean previous builds
    print_step "Cleaning previous builds..."
    make clean-build
    print_success "Clean completed"

    # Setup environment
    print_step "Setting up UV environment..."
    make setup
    print_success "Environment ready"

    # Run validation if enabled
    if [ "$VALIDATE" = "true" ]; then
        print_step "Validating build readiness..."
        if make validate-build; then
            print_success "Validation passed"
        else
            print_error "Validation failed"
            exit 1
        fi
    fi

    # Build based on type
    case "$BUILD_TYPE" in
        wheel)
            print_step "Building wheel..."
            make wheel
            print_success "Wheel built"
            ;;
        binary)
            print_step "Building binary..."
            make binary
            print_success "Binary built"
            ;;
        full)
            print_step "Building all targets..."
            make build
            print_success "All builds completed"
            ;;
    esac

    # Run tests if enabled
    if [ "$RUN_TESTS" = "true" ]; then
        print_step "Running tests..."
        if make test; then
            print_success "Tests passed"
        else
            print_error "Tests failed"
            exit 1
        fi
    fi

    # Show build artifacts
    print_step "Build artifacts:"
    if [ -d "dist" ]; then
        ls -lh dist/
    fi
    if [ -d "bin" ]; then
        ls -lh bin/
    fi

    # Publish if requested
    if [ "$PUBLISH" = "true" ]; then
        print_warning "Publishing to PyPI..."
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            make publish
            print_success "Published to PyPI"
        else
            print_warning "Publish cancelled"
        fi
    fi

    if [ "$PUBLISH_TEST" = "true" ]; then
        print_step "Publishing to Test PyPI..."
        make publish-test
        print_success "Published to Test PyPI"
    fi

    # Show summary
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}Build Completed Successfully!${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
    echo "Next steps:"
    echo "  • Test installation: uv pip install dist/*.whl"
    echo "  • Test binary: ./bin/mcli --help"
    echo "  • Publish: make publish"
    echo "  • Update version: make bump-version VERSION=x.y.z"
    echo ""
}

main "$@"
