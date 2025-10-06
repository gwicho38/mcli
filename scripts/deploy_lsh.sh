#!/bin/bash
# deploy_lsh.sh - Deploy LSH Daemon to fly.io
#
# This script automates the deployment of the LSH daemon to fly.io.
#
# Usage:
#   ./scripts/deploy_lsh.sh [options]
#
# Options:
#   --app NAME        Fly.io app name (default: mcli-lsh-daemon)
#   --region REGION   Deployment region (default: sjc)
#   --setup           Run initial setup (create app, set secrets)
#   --deploy-only     Only deploy (skip setup)
#   --test            Test deployment after deploy
#   --help            Show this help message
#
# Examples:
#   ./scripts/deploy_lsh.sh --setup
#   ./scripts/deploy_lsh.sh --deploy-only
#   ./scripts/deploy_lsh.sh --app my-lsh --region iad --setup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
APP_NAME="mcli-lsh-daemon"
REGION="sjc"
DO_SETUP=false
DO_DEPLOY=true
DO_TEST=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --app)
            APP_NAME="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --setup)
            DO_SETUP=true
            shift
            ;;
        --deploy-only)
            DO_SETUP=false
            shift
            ;;
        --test)
            DO_TEST=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --app NAME        Fly.io app name (default: mcli-lsh-daemon)"
            echo "  --region REGION   Deployment region (default: sjc)"
            echo "  --setup           Run initial setup (create app, set secrets)"
            echo "  --deploy-only     Only deploy (skip setup)"
            echo "  --test            Test deployment after deploy"
            echo "  --help            Show this help message"
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

    # Check if fly CLI is installed
    if ! command -v fly &> /dev/null; then
        print_error "fly CLI is not installed"
        echo "Install with: curl -L https://fly.io/install.sh | sh"
        exit 1
    fi
    print_success "fly CLI is installed"

    # Check if logged in to fly.io
    if ! fly auth whoami &> /dev/null; then
        print_error "Not logged in to fly.io"
        echo "Run: fly auth login"
        exit 1
    fi
    print_success "Logged in to fly.io"

    # Check if required files exist
    if [ ! -f "fly.lsh.toml" ]; then
        print_error "fly.lsh.toml not found"
        exit 1
    fi
    print_success "fly.lsh.toml found"

    if [ ! -f "Dockerfile.lsh" ]; then
        print_error "Dockerfile.lsh not found"
        exit 1
    fi
    print_success "Dockerfile.lsh found"

    # Check if .env file exists (for secrets)
    if [ ! -f ".env" ]; then
        print_warning ".env file not found"
        print_info "You'll need to set secrets manually with: fly secrets set"
    fi
}

# Create fly.io app
create_app() {
    print_header "Creating fly.io App"

    if fly apps list | grep -q "$APP_NAME"; then
        print_warning "App $APP_NAME already exists"
        return 0
    fi

    print_info "Creating app: $APP_NAME in region: $REGION"
    fly apps create "$APP_NAME" --org personal || {
        print_error "Failed to create app"
        exit 1
    }

    print_success "App created: $APP_NAME"
}

# Set secrets
set_secrets() {
    print_header "Setting Secrets"

    if [ ! -f ".env" ]; then
        print_warning ".env file not found, skipping automatic secret setup"
        print_info "Set secrets manually with:"
        echo ""
        echo "  fly secrets set LSH_API_KEY=your_key -a $APP_NAME"
        echo "  fly secrets set SUPABASE_URL=your_url -a $APP_NAME"
        echo "  fly secrets set SUPABASE_KEY=your_key -a $APP_NAME"
        echo ""
        return 0
    fi

    print_info "Reading secrets from .env file"

    # Extract secrets from .env
    LSH_API_KEY=$(grep "^LSH_API_KEY=" .env | cut -d'=' -f2-)
    SUPABASE_URL=$(grep "^SUPABASE_URL=" .env | cut -d'=' -f2-)
    SUPABASE_KEY=$(grep "^SUPABASE_KEY=" .env | cut -d'=' -f2-)
    SUPABASE_SERVICE_ROLE_KEY=$(grep "^SUPABASE_SERVICE_ROLE_KEY=" .env | cut -d'=' -f2-)

    # Set secrets
    if [ -n "$LSH_API_KEY" ]; then
        fly secrets set "LSH_API_KEY=$LSH_API_KEY" -a "$APP_NAME"
        print_success "LSH_API_KEY set"
    fi

    if [ -n "$SUPABASE_URL" ]; then
        fly secrets set "SUPABASE_URL=$SUPABASE_URL" -a "$APP_NAME"
        print_success "SUPABASE_URL set"
    fi

    if [ -n "$SUPABASE_KEY" ]; then
        fly secrets set "SUPABASE_KEY=$SUPABASE_KEY" -a "$APP_NAME"
        print_success "SUPABASE_KEY set"
    fi

    if [ -n "$SUPABASE_SERVICE_ROLE_KEY" ]; then
        fly secrets set "SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY" -a "$APP_NAME"
        print_success "SUPABASE_SERVICE_ROLE_KEY set"
    fi
}

# Deploy to fly.io
deploy() {
    print_header "Deploying to fly.io"

    print_info "Deploying app: $APP_NAME"
    fly deploy --config fly.lsh.toml -a "$APP_NAME" || {
        print_error "Deployment failed"
        exit 1
    }

    print_success "Deployment successful"
}

# Test deployment
test_deployment() {
    print_header "Testing Deployment"

    APP_URL="https://${APP_NAME}.fly.dev"

    print_info "Testing health endpoint: ${APP_URL}/health"

    # Wait for deployment to be ready
    sleep 5

    # Test health endpoint
    HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${APP_URL}/health" || echo "000")
    HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)

    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Health check passed"
        echo "$HEALTH_RESPONSE" | head -n -1
    else
        print_error "Health check failed (HTTP $HTTP_CODE)"
        print_info "Check logs with: fly logs -a $APP_NAME"
        exit 1
    fi

    # Test status endpoint
    print_info "Testing status endpoint: ${APP_URL}/status"
    STATUS_RESPONSE=$(curl -s "${APP_URL}/status" || echo "{}")
    if [ -n "$STATUS_RESPONSE" ]; then
        print_success "Status endpoint accessible"
        echo "$STATUS_RESPONSE"
    else
        print_warning "Status endpoint may not be available"
    fi
}

# Show post-deployment info
show_info() {
    print_header "Deployment Complete"

    APP_URL="https://${APP_NAME}.fly.dev"

    echo -e "${GREEN}🎉 LSH Daemon deployed successfully!${NC}"
    echo ""
    echo -e "${BLUE}App URL:${NC}      $APP_URL"
    echo -e "${BLUE}Health:${NC}       ${APP_URL}/health"
    echo -e "${BLUE}Status:${NC}       ${APP_URL}/status"
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    echo "  View logs:       fly logs -a $APP_NAME"
    echo "  View status:     fly status -a $APP_NAME"
    echo "  SSH console:     fly ssh console -a $APP_NAME"
    echo "  Dashboard:       fly dashboard -a $APP_NAME"
    echo ""
    echo -e "${BLUE}Configure mcli dashboard:${NC}"
    echo "  export LSH_API_URL=$APP_URL"
    echo "  mcli lsh-status"
    echo ""
}

# Main execution
main() {
    print_header "LSH Daemon Deployment Script"

    check_prerequisites

    if [ "$DO_SETUP" = true ]; then
        create_app
        set_secrets
    fi

    if [ "$DO_DEPLOY" = true ]; then
        deploy
    fi

    if [ "$DO_TEST" = true ]; then
        test_deployment
    fi

    show_info
}

# Run main function
main
