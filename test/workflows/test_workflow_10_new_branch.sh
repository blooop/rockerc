#!/bin/bash

# Test workflow for creating new branch and checking git status with prune functionality
# This test verifies that renv can create worktrees for new branches that don't exist yet
# and that the prune commands work correctly with the new branch workflow

set -e

# Cleanup function
cleanup() {
    echo "Cleaning up test environment..."
    # Use renv prune to clean up properly
    renv --prune 2>/dev/null || true
    # Fallback cleanup in case prune fails
    docker container prune -f --filter "label=renv" 2>/dev/null || true
    rm -rf ~/.renv 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT

echo "=== TEST: NEW BRANCH WORKFLOW WITH PRUNE ==="

# Initial cleanup to ensure clean state
echo "=== STEP 1: INITIAL CLEANUP ==="
renv --prune 2>/dev/null || true
echo "✓ Initial cleanup completed"

# Test creating a worktree for a new branch that doesn't exist
echo "=== STEP 2: CREATE NEW BRANCH ENVIRONMENT ==="
echo "Testing renv with new branch 'new_branch' that doesn't exist yet..."

# Run renv with a new branch and execute git status
renv blooop/test_renv@new_branch git status

echo "✓ Successfully created worktree for new branch and ran git status"

# Verify the branch was created and workspace is clean
echo "=== STEP 3: VERIFY NEW BRANCH ENVIRONMENT ==="
echo "Verifying the new branch was created properly..."

# Get the output to check it contains expected elements
OUTPUT=$(renv blooop/test_renv@new_branch git status 2>&1)

# Check that we're on the new branch
if echo "$OUTPUT" | grep -q "On branch new_branch"; then
    echo "✓ Confirmed on new branch 'new_branch'"
else
    echo "✗ Not on expected branch 'new_branch'"
    echo "Git status output: $OUTPUT"
    exit 1
fi

# Check that the workspace is clean (no uncommitted changes)
if echo "$OUTPUT" | grep -q "nothing to commit, working tree clean"; then
    echo "✓ Workspace is clean as expected"
else
    echo "✗ Workspace is not clean"
    echo "Git status output: $OUTPUT"
    exit 1
fi

# Verify container exists
echo "=== STEP 4: VERIFY CONTAINER EXISTS ==="
if docker ps --format "table {{.Names}}" | grep "test_renv-new-branch"; then
    echo "✓ Container for new branch environment is running"
else
    echo "✗ Container for new branch environment not found"
    docker ps
    exit 1
fi

# Test selective prune - should remove only the new branch environment
echo "=== STEP 5: TEST SELECTIVE PRUNE ==="
renv --prune blooop/test_renv@new_branch
echo "✓ Selective prune completed"

# Verify specific container is gone
if docker ps --format "table {{.Names}}" | grep "test_renv-new-branch"; then
    echo "✗ Container should have been removed by selective prune"
    docker ps
    exit 1
else
    echo "✓ Container correctly removed by selective prune"
fi

# Verify worktree is gone
if [ -d ~/.renv/workspaces/blooop/test_renv/worktree-new_branch ]; then
    echo "✗ Worktree should have been removed by selective prune"
    exit 1
else
    echo "✓ Worktree correctly removed by selective prune"
fi

# Recreate environment for full prune test
echo "=== STEP 6: RECREATE ENVIRONMENT FOR FULL PRUNE TEST ==="
renv blooop/test_renv@new_branch git status > /dev/null
echo "✓ Environment recreated"

# Test full prune - should remove everything
echo "=== STEP 7: TEST FULL PRUNE ==="
renv --prune
echo "✓ Full prune completed"

# Verify all renv containers are gone
if docker ps --format "table {{.Names}}" | grep -E "(test_renv|renv-)"; then
    echo "✗ No renv containers should exist after full prune"
    docker ps
    exit 1
else
    echo "✓ All renv containers correctly removed by full prune"
fi

# Verify .renv directory is gone
if [ -d ~/.renv ]; then
    echo "✗ .renv directory should have been removed by full prune"
    exit 1
else
    echo "✓ .renv directory correctly removed by full prune"
fi

# Final test: Verify workflow still works after full prune
echo "=== STEP 8: VERIFY WORKFLOW WORKS AFTER FULL PRUNE ==="
FINAL_OUTPUT=$(renv blooop/test_renv@new_branch git status 2>&1)

if echo "$FINAL_OUTPUT" | grep -q "On branch new_branch"; then
    echo "✓ New branch workflow still works after full prune"
else
    echo "✗ New branch workflow failed after full prune"
    echo "Output: $FINAL_OUTPUT"
    exit 1
fi

echo "=== NEW BRANCH WORKFLOW WITH PRUNE TEST PASSED ==="