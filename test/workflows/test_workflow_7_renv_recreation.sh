#!/usr/bin/env bash
set -e
cd /tmp

echo "=== TESTING worktree_docker RECREATION AFTER DELETION ==="
echo "This test verifies that worktree_docker works correctly after deleting the .worktree_docker folder"
echo

# Step 1: Test normal operation
echo "=== STEP 1: Normal worktree_docker operation ==="
echo "Running: worktree_docker blooop/test_wtd date"
worktree_docker blooop/test_wtd date
echo "SUCCESS: Initial worktree_docker operation completed"
echo

# Step 2: Delete .worktree_docker folder completely
echo "=== STEP 2: Deleting .worktree_docker folder ==="
echo "Removing ~/.worktree_docker folder completely..."
rm -rf ~/.worktree_docker
echo "SUCCESS: .worktree_docker folder deleted"
echo

# Step 3: Test worktree_docker recreation and operation
echo "=== STEP 3: Testing worktree_docker recreation ==="
echo "Running: worktree_docker blooop/test_wtd date (should recreate everything)"
worktree_docker blooop/test_wtd date
echo "SUCCESS: worktree_docker recreated and operated correctly"
echo

# Step 4: Test that subsequent operations work normally
echo "=== STEP 4: Testing subsequent operations ==="
echo "Running: worktree_docker blooop/test_wtd git status"
worktree_docker blooop/test_wtd git status
echo "SUCCESS: Subsequent operations work correctly"
echo

echo "=== ALL TESTS PASSED ==="
echo "worktree_docker successfully handles .worktree_docker folder deletion and recreation"