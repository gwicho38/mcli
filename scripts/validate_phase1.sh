#!/usr/bin/env bash
# Phase 1 Implementation Validation Script
# Tests all Phase 1 features to ensure they work correctly

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
TESTS=0

# Test result function
test_result() {
    local test_name="$1"
    local result="$2"
    local message="${3:-}"

    TESTS=$((TESTS + 1))

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        if [ -n "$message" ]; then
            echo -e "  ${YELLOW}Error: $message${NC}"
        fi
        FAILED=$((FAILED + 1))
    fi
}

# Test header
test_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Phase 1 Implementation Validation    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Test 1: MCLI Installation
test_header "Test 1: MCLI Installation"

if command -v mcli &> /dev/null; then
    test_result "MCLI command available" "PASS"

    # Test version
    if mcli --version &> /dev/null; then
        test_result "MCLI version check" "PASS"
    else
        test_result "MCLI version check" "FAIL" "mcli --version failed"
    fi
else
    test_result "MCLI command available" "FAIL" "mcli command not found in PATH"
fi

# Test 2: Core Modules
test_header "Test 2: Core Module Imports"

python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/mcli/src')

try:
    from mcli.lib.script_sync import ScriptSyncManager
    print("✓ script_sync module imports")
except ImportError as e:
    print(f"✗ script_sync import failed: {e}")
    sys.exit(1)

try:
    from mcli.lib.script_watcher import start_watcher
    print("✓ script_watcher module imports")
except ImportError as e:
    print(f"✗ script_watcher import failed: {e}")
    sys.exit(1)

try:
    from mcli.workflow.sync_cmd import sync_group
    print("✓ sync_cmd module imports")
except ImportError as e:
    print(f"✗ sync_cmd import failed: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    test_result "Core modules import successfully" "PASS"
else
    test_result "Core modules import successfully" "FAIL" "Module import errors"
fi

# Test 3: Script Sync Functionality
test_header "Test 3: Script Sync System"

# Create test directory if it doesn't exist
mkdir -p /tmp/mcli_test/commands/test

# Create a test script
cat > /tmp/mcli_test/commands/test/test_sync.sh << 'SCRIPT'
#!/usr/bin/env bash
# @description: Test script for validation
# @version: 1.0.0
# @author: MCLI Team
# @tags: test, validation

echo "Test script executed successfully"
SCRIPT

chmod +x /tmp/mcli_test/commands/test/test_sync.sh

# Test script sync
python3 << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, '/home/user/mcli/src')

try:
    from mcli.lib.script_sync import ScriptSyncManager

    # Initialize sync manager
    commands_dir = Path("/tmp/mcli_test/commands")
    sync_manager = ScriptSyncManager(commands_dir)

    # Test language detection
    script_path = commands_dir / "test/test_sync.sh"
    language = sync_manager.detect_language(script_path)
    assert language == "bash", f"Expected bash, got {language}"
    print("✓ Language detection works")

    # Test metadata extraction
    metadata = sync_manager.extract_metadata(script_path, language)
    assert metadata["description"] == "Test script for validation"
    assert metadata["version"] == "1.0.0"
    print("✓ Metadata extraction works")

    # Test hash calculation
    hash_value = sync_manager.calculate_hash(script_path)
    assert len(hash_value) == 64, "Hash should be SHA256 (64 chars)"
    print("✓ Hash calculation works")

    # Test JSON generation
    json_path = sync_manager.generate_json(script_path, group="test")
    assert json_path is not None, "JSON path should not be None"
    assert json_path.exists(), "JSON file should exist"
    print(f"✓ JSON generation works: {json_path}")

    # Verify JSON structure
    import json
    with open(json_path, 'r') as f:
        workflow = json.load(f)

    assert workflow["name"] == "test_sync"
    assert workflow["group"] == "test"
    assert workflow["language"] == "bash"
    assert workflow["description"] == "Test script for validation"
    print("✓ JSON structure is correct")

    print("SUCCESS: All script sync tests passed")

except Exception as e:
    print(f"ERROR: Script sync test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    test_result "Script sync system works" "PASS"
else
    test_result "Script sync system works" "FAIL" "Script sync tests failed"
fi

# Test 4: CLI Commands
test_header "Test 4: CLI Commands"

# Test sync commands exist
if mcli workflows --help 2>&1 | grep -q "sync"; then
    test_result "Sync commands registered" "PASS"
else
    test_result "Sync commands registered" "FAIL" "sync not found in workflows help"
fi

# Test 5: Workflow JSONs
test_header "Test 5: Example Workflow JSONs"

JSON_DIR="/home/user/mcli-commands"

for json_file in \
    "ml/training.json" \
    "ml/serving.json" \
    "ml/dashboard.json" \
    "trading/backtesting.json" \
    "trading/optimization.json" \
    "video/processing.json"
do
    if [ -f "$JSON_DIR/$json_file" ]; then
        # Validate JSON structure
        if python3 -c "import json; json.load(open('$JSON_DIR/$json_file'))" 2>/dev/null; then
            test_result "Workflow JSON: $json_file" "PASS"
        else
            test_result "Workflow JSON: $json_file" "FAIL" "Invalid JSON structure"
        fi
    else
        test_result "Workflow JSON: $json_file" "FAIL" "File not found"
    fi
done

# Test 6: Documentation Files
test_header "Test 6: Documentation"

DOC_FILES=(
    "/home/user/mcli/docs/SCRIPT_SYNC_SYSTEM.md"
    "/home/user/mcli/docs/SCOPE_MIGRATION_PLAN.md"
    "/home/user/mcli/docs/MIGRATION_GUIDE_V8.md"
    "/home/user/mcli/IMPLEMENTATION_COMPLETE.md"
    "/home/user/mcli/PHASE_2_READY.md"
    "/home/user/mcli-commands/README.md"
)

for doc_file in "${DOC_FILES[@]}"; do
    filename=$(basename "$doc_file")
    if [ -f "$doc_file" ]; then
        # Check if file has content
        if [ -s "$doc_file" ]; then
            test_result "Documentation: $filename" "PASS"
        else
            test_result "Documentation: $filename" "FAIL" "File is empty"
        fi
    else
        test_result "Documentation: $filename" "FAIL" "File not found"
    fi
done

# Test 7: Plugin System
test_header "Test 7: Plugin System in pyproject.toml"

if grep -q "ml-plugin" /home/user/mcli/pyproject.toml; then
    test_result "ml-plugin defined" "PASS"
else
    test_result "ml-plugin defined" "FAIL" "ml-plugin not found in pyproject.toml"
fi

if grep -q "trading-plugin" /home/user/mcli/pyproject.toml; then
    test_result "trading-plugin defined" "PASS"
else
    test_result "trading-plugin defined" "FAIL" "trading-plugin not found in pyproject.toml"
fi

if grep -q "video-plugin" /home/user/mcli/pyproject.toml; then
    test_result "video-plugin defined" "PASS"
else
    test_result "video-plugin defined" "FAIL" "video-plugin not found in pyproject.toml"
fi

# Test 8: Migration Script
test_header "Test 8: Migration Helper Script"

MIGRATION_SCRIPT="/home/user/mcli/scripts/migrate_features.py"

if [ -f "$MIGRATION_SCRIPT" ]; then
    test_result "Migration script exists" "PASS"

    # Test if script is executable
    if python3 "$MIGRATION_SCRIPT" --help &> /dev/null; then
        test_result "Migration script executable" "PASS"
    else
        test_result "Migration script executable" "FAIL" "Script --help failed"
    fi
else
    test_result "Migration script exists" "FAIL" "File not found"
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Validation Summary             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total Tests:  ${BLUE}$TESTS${NC}"
echo -e "Passed:       ${GREEN}$PASSED${NC}"
echo -e "Failed:       ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✓ ALL TESTS PASSED                  ║${NC}"
    echo -e "${GREEN}║   Phase 1 Implementation Valid!       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ✗ SOME TESTS FAILED                  ║${NC}"
    echo -e "${RED}║   Please review failures above         ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════╝${NC}"
    exit 1
fi
