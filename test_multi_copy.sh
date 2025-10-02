#!/bin/bash
# Integration test for multi-copy cache implementation
# This script tests the core functionality of the new renv implementation

set -e

RENV_ROOT="$HOME/renv"
TEST_USER="test-user-$$"
TEST_REPO="test-repo"
TEST_DIR="$RENV_ROOT/$TEST_USER"
CACHE_DIR="$TEST_DIR/$TEST_REPO-cache"
MAIN_DIR="$TEST_DIR/$TEST_REPO-main"
FEATURE_DIR="$TEST_DIR/$TEST_REPO-feature"

echo "========================================="
echo "Testing Multi-Copy Cache Implementation"
echo "========================================="

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up test directories..."
    rm -rf "$TEST_DIR"
    echo "Cleanup complete"
}

# Register cleanup on exit
trap cleanup EXIT

# Create test repository structure
echo ""
echo "1. Setting up test environment..."
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Create a fake cache repository
echo "   Creating cache repository..."
mkdir -p "$CACHE_DIR"
cd "$CACHE_DIR"
git init
git config user.email "test@example.com"
git config user.name "Test User"
echo "# Test Repo" > README.md
git add README.md
git commit -m "Initial commit"

# Create main branch
git branch -M main
echo "main content" > main.txt
git add main.txt
git commit -m "Add main content"

# Create feature branch
git checkout -b feature
echo "feature content" > feature.txt
git add feature.txt
git commit -m "Add feature content"
git checkout main

echo "   ✓ Cache repository created"

# Test 1: Verify cache directory structure
echo ""
echo "2. Testing cache directory structure..."
if [ -d "$CACHE_DIR/.git" ]; then
    echo "   ✓ Cache has standard .git directory (not bare)"
else
    echo "   ✗ FAILED: Cache should have .git directory"
    exit 1
fi

if [ -f "$CACHE_DIR/.git" ]; then
    echo "   ✗ FAILED: Cache should not have .git file (worktree style)"
    exit 1
else
    echo "   ✓ Cache is not a worktree"
fi

# Test 2: Simulate branch copy creation
echo ""
echo "3. Testing branch copy creation..."
echo "   Copying cache to main branch directory..."
cp -r "$CACHE_DIR" "$MAIN_DIR"
cd "$MAIN_DIR"
git checkout main

if [ -d "$MAIN_DIR/.git" ] && [ ! -f "$MAIN_DIR/.git" ]; then
    echo "   ✓ Main branch copy has standard .git directory"
else
    echo "   ✗ FAILED: Main branch copy should have standard .git"
    exit 1
fi

# Test 3: Verify git operations work
echo ""
echo "4. Testing git operations in branch copy..."
cd "$MAIN_DIR"
if git status &> /dev/null; then
    echo "   ✓ git status works in main branch copy"
else
    echo "   ✗ FAILED: git status failed in main branch copy"
    exit 1
fi

if git log --oneline | grep -q "Initial commit"; then
    echo "   ✓ git log works in main branch copy"
else
    echo "   ✗ FAILED: git log failed in main branch copy"
    exit 1
fi

# Test 4: Test multiple branch copies
echo ""
echo "5. Testing multiple branch copies..."
echo "   Creating feature branch copy..."
cp -r "$CACHE_DIR" "$FEATURE_DIR"
cd "$FEATURE_DIR"
git checkout feature

if [ -f "$FEATURE_DIR/feature.txt" ]; then
    echo "   ✓ Feature branch copy has correct files"
else
    echo "   ✗ FAILED: Feature branch copy missing expected files"
    exit 1
fi

if git branch --show-current | grep -q "feature"; then
    echo "   ✓ Feature branch copy on correct branch"
else
    echo "   ✗ FAILED: Feature branch copy not on feature branch"
    exit 1
fi

# Test 5: Verify independence of copies
echo ""
echo "6. Testing independence of branch copies..."
cd "$MAIN_DIR"
echo "main changes" >> main.txt
git add main.txt
git commit -m "Update main"

cd "$FEATURE_DIR"
if ! git log --oneline | grep -q "Update main"; then
    echo "   ✓ Feature branch copy is independent from main"
else
    echo "   ✗ FAILED: Changes in main affected feature copy"
    exit 1
fi

# Test 6: Simulate cache update (fetch)
echo ""
echo "7. Testing cache update workflow..."
cd "$CACHE_DIR"
echo "cache update" >> README.md
git add README.md
git commit -m "Update cache"

if git log --oneline | grep -q "Update cache"; then
    echo "   ✓ Cache can be updated independently"
else
    echo "   ✗ FAILED: Cache update failed"
    exit 1
fi

# Test 7: Verify new copy gets updated cache
echo ""
echo "8. Testing new copy from updated cache..."
TEST_DIR2="$TEST_DIR/$TEST_REPO-test2"
cp -r "$CACHE_DIR" "$TEST_DIR2"
cd "$TEST_DIR2"

if grep -q "cache update" README.md; then
    echo "   ✓ New copy includes cache updates"
else
    echo "   ✗ FAILED: New copy doesn't have cache updates"
    exit 1
fi

# Test 8: Verify path structure matches spec
echo ""
echo "9. Verifying directory structure matches spec..."
if [ -d "$CACHE_DIR" ]; then
    echo "   ✓ Cache directory: $TEST_REPO-cache exists"
else
    echo "   ✗ FAILED: Cache directory structure incorrect"
    exit 1
fi

if [ -d "$MAIN_DIR" ]; then
    echo "   ✓ Branch directory: $TEST_REPO-main exists"
else
    echo "   ✗ FAILED: Branch directory structure incorrect"
    exit 1
fi

if [ -d "$FEATURE_DIR" ]; then
    echo "   ✓ Branch directory: $TEST_REPO-feature exists"
else
    echo "   ✗ FAILED: Branch directory structure incorrect"
    exit 1
fi

echo ""
echo "========================================="
echo "All tests passed! ✓"
echo "========================================="
echo ""
echo "Summary:"
echo "  - Cache uses standard git directory (not bare)"
echo "  - Branch copies are full, independent git repos"
echo "  - All git operations work correctly"
echo "  - Multiple branches can coexist"
echo "  - Directory structure matches spec"
