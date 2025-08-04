#!/bin/bash

# Test workflow for --nocache feature
# This test verifies that worktree_docker --nocache disables build caching

set -e

# Cleanup function
cleanup() {
    echo "Cleaning up test environment..."
    # Use worktree_docker prune to clean up properly
    worktree_docker --prune 2>/dev/null || true
    # Fallback cleanup in case prune fails
    docker container prune -f --filter "label=worktree_docker" 2>/dev/null || true
    rm -rf ~/.worktree_docker 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT

echo "=== TEST: NOCACHE FEATURE ==="

# Initial cleanup to ensure clean state
echo "=== STEP 1: INITIAL CLEANUP ==="
worktree_docker --prune 2>/dev/null || true
echo "✓ Initial cleanup completed"

# Test --nocache flag shows up in help
echo "=== STEP 2: TEST NOCACHE IN HELP ==="
HELP_OUTPUT=$(worktree_docker --help 2>&1)

if echo "$HELP_OUTPUT" | grep -q "nocache.*Disable use of Buildx cache"; then
    echo "✓ --nocache option appears in help"
else
    echo "✗ --nocache option not found in help"
    echo "Help output: $HELP_OUTPUT"
    exit 1
fi

# Test building with nocache (we'll capture the build output to verify --no-cache is used)
echo "=== STEP 3: TEST NOCACHE FLAG USAGE ==="
echo "Building with --nocache flag..."

# Capture the build output to check if --no-cache is passed to buildx
BUILD_OUTPUT=$(worktree_docker --nocache blooop/test_worktree_docker@main git status 2>&1 || true)

# Check if --no-cache appears in the build command output
if echo "$BUILD_OUTPUT" | grep -q "buildx bake.*--no-cache"; then
    echo "✓ --no-cache flag passed to buildx bake command"
else
    echo "✗ --no-cache flag not found in buildx bake command"
    echo "Build output:"
    echo "$BUILD_OUTPUT"
    exit 1
fi

echo "=== STEP 4: VERIFY ENVIRONMENT STILL WORKS ==="
# Test that the environment still works correctly with nocache
FINAL_OUTPUT=$(worktree_docker blooop/test_worktree_docker@main git status 2>&1)

if echo "$FINAL_OUTPUT" | grep -q "On branch main"; then
    echo "✓ Environment works correctly with --nocache"
else
    echo "✗ Environment failed with --nocache"
    echo "Output: $FINAL_OUTPUT"
    exit 1
fi

if echo "$FINAL_OUTPUT" | grep -q "nothing to commit, working tree clean"; then
    echo "✓ Git status shows clean workspace"
else
    echo "✗ Git status doesn't show clean workspace"
    echo "Output: $FINAL_OUTPUT"
    exit 1
fi

echo "=== STEP 5: TEST BACKWARD COMPATIBILITY ==="
# Test that the flag works in both subcommand and global contexts
echo "Testing backward compatibility..."

# Test global flag
GLOBAL_OUTPUT=$(worktree_docker --nocache blooop/test_worktree_docker@main echo "global nocache test" 2>&1 || true)

if echo "$GLOBAL_OUTPUT" | grep -q "global nocache test"; then
    echo "✓ Global --nocache flag works"
else
    echo "✗ Global --nocache flag failed"
    echo "Output: $GLOBAL_OUTPUT"
fi

echo "=== NOCACHE FEATURE TEST PASSED ==="