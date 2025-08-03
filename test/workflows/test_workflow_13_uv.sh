#!/bin/bash

# Test workflow for uv extension
# This test verifies that the uv Python package manager extension loads and works correctly

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

echo "=== TEST: UV EXTENSION ==="

# Initial cleanup to ensure clean state
echo "=== STEP 1: INITIAL CLEANUP ==="
renv prune 2>/dev/null || true
echo "✓ Initial cleanup completed"

# Test that uv extension appears in extension list
echo "=== STEP 2: TEST UV EXTENSION IN LIST ==="
EXT_LIST_OUTPUT=$(renv ext list 2>&1)

if echo "$EXT_LIST_OUTPUT" | grep -q "uv"; then
    echo "✓ uv extension appears in extension list"
else
    echo "✗ uv extension not found in extension list"
    echo "Extension list output: $EXT_LIST_OUTPUT"
    exit 1
fi

# Test loading uv extension explicitly
echo "=== STEP 3: TEST UV EXTENSION LOADING ==="
echo "Testing uv extension loading with test repository..."

# Capture output to check if uv extension is loaded
LOAD_OUTPUT=$(timeout 60 renv launch blooop/test_renv@main --rebuild --extensions uv echo "uv extension test" 2>&1 || true)

# Check if uv extension was loaded
if echo "$LOAD_OUTPUT" | grep -q "✓ Loaded extension: uv"; then
    echo "✓ uv extension loaded successfully"
else
    echo "✗ uv extension failed to load"
    echo "Load output:"
    echo "$LOAD_OUTPUT"
    exit 1
fi

# Check if the command executed properly
if echo "$LOAD_OUTPUT" | grep -q "uv extension test"; then
    echo "✓ Command executed successfully with uv extension"
else
    echo "✗ Command failed to execute with uv extension"
    echo "Load output:"
    echo "$LOAD_OUTPUT"
    exit 1
fi

# Test that uv is available in the container
echo "=== STEP 4: TEST UV AVAILABILITY IN CONTAINER ==="
UV_TEST_OUTPUT=$(timeout 60 renv launch blooop/test_renv@main --extensions uv which uv 2>&1 || true)

if echo "$UV_TEST_OUTPUT" | grep -q "uv"; then
    echo "✓ uv is available in container and shows version"
else
    echo "✗ uv is not available in container"
    echo "UV test output:"
    echo "$UV_TEST_OUTPUT"
    exit 1
fi

# Test basic uv functionality
echo "=== STEP 5: TEST UV BASIC FUNCTIONALITY ==="
UV_FUNC_OUTPUT=$(timeout 60 renv launch blooop/test_renv@main --extensions uv uv --help 2>&1 || true)

if echo "$UV_FUNC_OUTPUT" | grep -q "usage"; then
    echo "✓ uv help command works correctly"
else
    echo "✗ uv help command failed"
    echo "UV function test output:"
    echo "$UV_FUNC_OUTPUT"
    exit 1
fi

echo "=== STEP 6: TEST UV WITH OTHER EXTENSIONS ==="
# Test that uv works with other common extensions
MULTI_EXT_OUTPUT=$(timeout 60 renv launch blooop/test_renv@main --extensions git uv echo "multi-extension test" 2>&1 || true)

if echo "$MULTI_EXT_OUTPUT" | grep -q "✓ Loaded extension: git" && echo "$MULTI_EXT_OUTPUT" | grep -q "✓ Loaded extension: uv"; then
    echo "✓ uv extension works with other extensions"
else
    echo "✗ uv extension failed to work with other extensions"
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

echo "=== UV EXTENSION TEST PASSED ==="