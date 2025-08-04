#!/usr/bin/env bash
set -e
cd /tmp

echo "=== TESTING RENV RECREATION AFTER DELETION ==="
echo "This test verifies that renv works correctly after deleting the .renv folder"
echo

# Step 1: Test normal operation
echo "=== STEP 1: Normal renv operation ==="
echo "Running: renv blooop/test_wtd date"
renv blooop/test_wtd date
echo "SUCCESS: Initial renv operation completed"
echo

# Step 2: Delete .renv folder completely
echo "=== STEP 2: Deleting .renv folder ==="
echo "Removing ~/.renv folder completely..."
rm -rf ~/.renv
echo "SUCCESS: .renv folder deleted"
echo

# Step 3: Test renv recreation and operation
echo "=== STEP 3: Testing renv recreation ==="
echo "Running: renv blooop/test_wtd date (should recreate everything)"
renv blooop/test_wtd date
echo "SUCCESS: renv recreated and operated correctly"
echo

# Step 4: Test that subsequent operations work normally
echo "=== STEP 4: Testing subsequent operations ==="
echo "Running: renv blooop/test_wtd git status"
renv blooop/test_wtd git status
echo "SUCCESS: Subsequent operations work correctly"
echo

echo "=== ALL TESTS PASSED ==="
echo "renv successfully handles .renv folder deletion and recreation"