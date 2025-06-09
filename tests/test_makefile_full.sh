#!/usr/bin/env bash
# test_makefile_full.sh - Full test script for Makefile targets with UV

# Colors for pretty output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"
CHECKMARK="✅"
CROSSMARK="❌"

# Log file
LOG_FILE="test_makefile_full.log"
rm -f "$LOG_FILE"
touch "$LOG_FILE"

# Initialize counters
PASSED=0
FAILED=0
SKIPPED=0
TOTAL=0

# Helper functions
log() {
  echo -e "$1" | tee -a "$LOG_FILE"
}

log_test() {
  echo -e "\n${CYAN}=== Testing target: $1 ===${RESET}" | tee -a "$LOG_FILE"
  TOTAL=$((TOTAL + 1))
}

log_pass() {
  log "${GREEN}${CHECKMARK} PASS: $1${RESET}"
  PASSED=$((PASSED + 1))
}

log_fail() {
  log "${RED}${CROSSMARK} FAIL: $1${RESET}"
  FAILED=$((FAILED + 1))
}

log_skip() {
  log "${YELLOW}⚠ SKIP: $1${RESET}"
  SKIPPED=$((SKIPPED + 1))
}

run_test() {
  local target="$1"
  local skip_reason="$2"
  local timeout_seconds="${3:-180}"  # Default 3 minute timeout
  
  log_test "$target"
  
  if [ -n "$skip_reason" ]; then
    log_skip "$target - $skip_reason"
    return
  fi
  
  # First try a dry run
  if ! make "$target" -n > /dev/null 2>&1; then
    log_fail "$target (dry-run verification failed)"
    return
  fi
  
  # Run the make target with a timeout
  if timeout $timeout_seconds make "$target" > "target_$target.log" 2>&1; then
    log_pass "$target"
    log "Output saved to target_$target.log"
  else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
      log_fail "$target (timeout after $timeout_seconds seconds)"
    else
      log_fail "$target (exit code $EXIT_CODE)"
    fi
    log "See target_$target.log for details"
  fi
}

# Pre-test setup
check_dependencies() {
  log "Checking dependencies..."
  
  # Check for required tools
  for cmd in make python uv timeout; do
    if command -v "$cmd" > /dev/null 2>&1; then
      log "✓ $cmd installed"
    else
      log "✗ $cmd not found - required for tests"
      return 1
    fi
  done
  
  # Check Python version
  python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "3.9")
  min_python="3.9"
  if [ "$(printf '%s\n' "$min_python" "$python_version" | sort -V | head -n1)" != "$min_python" ]; then
    log "✗ Python $python_version detected, but mcli requires Python $min_python+"
    return 1
  else
    log "✓ Python $python_version meets minimum requirement"
  fi
  
  # Check UV version
  uv_version=$(uv --version 2>/dev/null || echo "Not installed")
  log "✓ UV version: $uv_version"
  
  return 0
}

# Record system state
log "Full test of Makefile targets for UV compatibility"
log "Date: $(date)"
log "System: $(uname -a)"
log "Directory: $(pwd)"
log "-------------------------------------------"

# Check dependencies
if ! check_dependencies; then
  log "${RED}Dependency check failed. Please install required tools.${RESET}"
  exit 1
fi

# Test each target
log "\n-------------------------------------------"
log "Starting tests"
log "-------------------------------------------"

# Start with basic commands
run_test "help" ""
run_test "debug" ""
run_test "clean" ""

# Environment setup
run_test "setup" ""

# Build tests - these create actual artifacts
run_test "darwin" "" 300  # Allow 5 minutes for build

# We'll test after building, no need for a separate check here

# Test portable binary creation if wheel was built
# Force recreate dist directory if needed
mkdir -p dist

# Check for wheel files
if [ -d "dist" ] && [ "$(ls -A dist/*.whl 2>/dev/null | wc -l)" -gt 0 ]; then
  # Run the test target before portable to ensure package works
  run_test "test" "" 300  # Allow 5 minutes for test
  
  # Run portable build
  run_test "portable" "" 600  # Allow 10 minutes for portable build
  
  # Test binary if it was created
  if [ -d "bin" ] && [ "$(find bin -type f | wc -l)" -gt 0 ]; then
    run_test "test-binary" ""
  else
    run_test "test-binary" "Skipped because binary not found"
  fi
else
  run_test "test" "Skipped because wheel not found in dist directory"
  run_test "portable" "Skipped because wheel not found"
  run_test "test-binary" "Skipped because portable build was skipped"
fi

# Skip longer running or more complex tests
run_test "nuitka-app" "Skipped due to long build time (run manually)" 
run_test "nuitka-binary" "Skipped due to long build time (run manually)"
run_test "portable-py" "Skipped (requires Docker, run manually)"
run_test "linux-portable" "Skipped (requires Docker, run manually)"

# Cleanup
run_test "clean-all" "" 

# Print summary
log "\n-------------------------------------------"
log "Test Summary:"
log "  Total: $TOTAL"
log "  Passed: ${GREEN}$PASSED${RESET}"
log "  Failed: ${RED}$FAILED${RESET}"
log "  Skipped: ${YELLOW}$SKIPPED${RESET}"

# Set exit code based on test results
if [ $FAILED -gt 0 ]; then
  log "${RED}Some tests failed. See $LOG_FILE for details.${RESET}"
  exit 1
else
  log "${GREEN}All executed tests passed!${RESET}"
  exit 0
fi