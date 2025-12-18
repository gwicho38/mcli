#!/usr/bin/env bash
# test_makefile.sh - Test script for Makefile targets using UV

# Exit on error
set -e

# Colors for pretty output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"
CHECKMARK="✅"
CROSSMARK="❌"

# Set test mode to skip long-running or destructive commands
TEST_MODE=true
VERBOSE=${VERBOSE:-false}

# Test log file
LOG_FILE="test_makefile.log"
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
  
  log_test "$target"
  
  if [ -n "$skip_reason" ]; then
    log_skip "$target - $skip_reason"
    return
  fi
  
  # Backup any existing cache files to restore afterwards
  local cache_dir=".build_cache"
  if [ -d "$cache_dir" ]; then
    log "Backing up cache directory"
    cp -r "$cache_dir" "${cache_dir}.bak"
  fi
  
  # Run the make target with a timeout
  if $VERBOSE; then
    if timeout 60 make "$target" -n; then
      log_pass "$target (dry-run)"
    else
      log_fail "$target (dry-run)"
      return
    fi
  else
    if timeout 60 make "$target" -n > /dev/null 2>&1; then
      log_pass "$target (dry-run)"
    else
      log_fail "$target (dry-run)"
      return
    fi
  fi
  
  # Restore cache directory if it was backed up
  if [ -d "${cache_dir}.bak" ]; then
    log "Restoring cache directory"
    rm -rf "$cache_dir"
    mv "${cache_dir}.bak" "$cache_dir"
  fi
}

# Record system state
log "Testing Makefile targets for UV compatibility"
log "Date: $(date)"
log "Python: $(python --version)"
log "UV: $(uv --version 2>/dev/null || echo 'Not installed')"
log "Directory: $(pwd)"
log "Test mode: $TEST_MODE"
log "-------------------------------------------"

# Test each target
run_test "help" ""
run_test "debug" ""
run_test "clean" ""

# Skip clean-all in test mode as it's destructive
run_test "clean-all" "Skipped in test mode (destructive command)"

# Setup may take too long for a test
run_test "setup" "Skipped in test mode (long-running command)"

# Test basic build targets with dry-run only
run_test "darwin" "Skipped in test mode (long-running command)"
run_test "portable" ""

# Skip installation tests in test mode
run_test "install" "Skipped in test mode (system modification)"
run_test "install-app" "Skipped in test mode (system modification)"
run_test "install-binary" "Skipped in test mode (system modification)"
run_test "install-nuitka" "Skipped in test mode (system modification)"
run_test "install-portable" "Skipped in test mode (system modification)"
run_test "uninstall" "Skipped in test mode (system modification)"

# Nuitka builds would take too long for a test
run_test "nuitka-app" "Skipped in test mode (long-running command)"
run_test "nuitka-binary" "Skipped in test mode (long-running command)"

# Skip multi-version builds
run_test "portable-py" "Skipped in test mode (requires Docker)"
run_test "portable-versions" "Skipped in test mode (requires Docker)"
run_test "portable-all-versions" "Skipped in test mode (requires Docker)"
run_test "linux-portable" "Skipped in test mode (requires Docker)"

# Test targets
run_test "test" "Skipped in test mode (depends on successful build)"
run_test "test-binary" "Skipped in test mode (depends on successful build)"

# Skip force rebuild
run_test "force-rebuild" "Skipped in test mode (destructive and long-running)"

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