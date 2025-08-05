#!/usr/bin/env bash
set -e
cd /tmp

echo "=== TESTING RENV RECREATION AFTER DELETION ==="
echo "This test verifies that wtd works correctly after deleting the .wtd folder"
echo

# Step 1: Test normal operation
echo "=== STEP 1: Normal wtd operation ==="
echo "Running: wtd blooop/test_wtd date"
wtd blooop/test_wtd date
echo "SUCCESS: Initial wtd operation completed"
echo

# Step 2: Delete .wtd folder completely
echo "=== STEP 2: Deleting .wtd folder ==="
echo "Removing ~/.wtd folder completely..."
rm -rf ~/.wtd
echo "SUCCESS: .wtd folder deleted"
echo

# Step 3: Test wtd recreation and operation
echo "=== STEP 3: Testing wtd recreation ==="
echo "Running: wtd blooop/test_wtd date (should recreate everything)"
wtd blooop/test_wtd date
echo "SUCCESS: wtd recreated and operated correctly"
echo

# Step 4: Test that subsequent operations work normally
echo "=== STEP 4: Testing subsequent operations ==="
echo "Running: wtd blooop/test_wtd git status"
wtd blooop/test_wtd git status
echo "SUCCESS: Subsequent operations work correctly"
echo

echo "=== ALL TESTS PASSED ==="
echo "wtd successfully handles .wtd folder deletion and recreation"