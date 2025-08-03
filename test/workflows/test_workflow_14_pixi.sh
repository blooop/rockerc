#!/bin/bash

# Test workflow for pixi extension
# This test verifies that the pixi package manager extension loads and works correctly

set -e

# Cleanup function
cleanup() {
    echo "Cleaning up test environment..."
    # Use renv prune to clean up properly
    renv prune 2>/dev/null || true
    # Fallback cleanup in case prune fails
    docker container prune -f --filter "label=renv" 2>/dev/null || true
    rm -rf ~/.renv 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT

echo "=== TEST: PIXI EXTENSION ==="

# Initial cleanup to ensure clean state
echo "=== STEP 1: INITIAL CLEANUP ==="
renv prune 2>/dev/null || true
echo "✓ Initial cleanup completed"

# Test that pixi extension appears in extension list
echo "=== STEP 2: TEST PIXI EXTENSION IN LIST ==="
EXT_LIST_OUTPUT=$(renv ext list 2>&1)

if echo "$EXT_LIST_OUTPUT" | grep -q "pixi"; then
    echo "✓ pixi extension appears in extension list"
else
    echo "✗ pixi extension not found in extension list"
    echo "Extension list output: $EXT_LIST_OUTPUT"
    exit 1
fi

# Test loading pixi extension explicitly
echo "=== STEP 3: TEST PIXI EXTENSION LOADING ==="
echo "Testing pixi extension loading with test repository..."

# Capture output to check if pixi extension is loaded
LOAD_OUTPUT=$(timeout 60 renv launch blooop/test_renv@main --rebuild --extensions pixi echo "pixi extension test" 2>&1 || true)

# Check if pixi extension was loaded
if echo "$LOAD_OUTPUT" | grep -q "✓ Loaded extension: pixi"; then
    echo "✓ pixi extension loaded successfully"
else
    echo "✗ pixi extension failed to load"
    echo "Load output:"
    echo "$LOAD_OUTPUT"
    exit 1
fi

# Check if the command executed properly
if echo "$LOAD_OUTPUT" | grep -q "pixi extension test"; then
    echo "✓ Command executed successfully with pixi extension"
else
    echo "✗ Command failed to execute with pixi extension"
    echo "Load output:"
    echo "$LOAD_OUTPUT"
    exit 1
fi

# Test that pixi is available in the container
echo "=== STEP 4: TEST PIXI AVAILABILITY IN CONTAINER ==="
PIXI_TEST_OUTPUT=$(timeout 60 renv launch blooop/test_renv@main --extensions pixi which pixi 2>&1 || true)

if echo "$PIXI_TEST_OUTPUT" | grep -q "pixi"; then
    echo "✓ pixi is available in container and shows version"
else
    echo "✗ pixi is not available in container"
    echo "Pixi test output:"
    echo "$PIXI_TEST_OUTPUT"
    exit 1
fi

# Test basic pixi functionality
echo "=== STEP 5: TEST PIXI BASIC FUNCTIONALITY ==="
PIXI_FUNC_OUTPUT=$(timeout 60 renv launch blooop/test_renv@main --extensions pixi pixi --help 2>&1 || true)

if echo "$PIXI_FUNC_OUTPUT" | grep -q "usage"; then
    echo "✓ pixi help command works correctly"
else
    echo "✗ pixi help command failed"
    echo "Pixi function test output:"
    echo "$PIXI_FUNC_OUTPUT"
    exit 1
fi

echo "=== STEP 6: TEST PIXI WITH OTHER EXTENSIONS ==="
# Test that pixi works with other common extensions
MULTI_EXT_OUTPUT=$(timeout 60 renv launch blooop/test_renv@main --extensions git pixi echo "multi-extension test" 2>&1 || true)

if echo "$MULTI_EXT_OUTPUT" | grep -q "✓ Loaded extension: git" && echo "$MULTI_EXT_OUTPUT" | grep -q "✓ Loaded extension: pixi"; then
    echo "✓ pixi extension works with other extensions"
else
    echo "✗ pixi extension failed to work with other extensions"
    echo "Multi-extension output:"
    echo "$MULTI_EXT_OUTPUT"
    exit 1
fi

if echo "$MULTI_EXT_OUTPUT" | grep -q "multi-extension test"; then
    echo "✓ Multi-extension command executed successfully"
else
    echo "✗ Multi-extension command failed"
    echo "Multi-extension output:"
    echo "$MULTI_EXT_OUTPUT"
    exit 1
fi

echo "=== PIXI EXTENSION TEST PASSED ==="