#!/usr/bin/env bash
set -e

echo "=== worktree_docker PRUNE FUNCTIONALITY TEST ==="
echo "Testing both selective and full prune operations"

# Clean up any existing test containers and cache
echo "=== INITIAL CLEANUP ==="
rm -rf ~/.worktree_docker || true
docker container stop test_worktree_docker-main 2>/dev/null || true
docker rm -f test_worktree_docker-main 2>/dev/null || true
echo "Cleaned up existing test environment"

# Test 1: Set up test environment
echo "=== TEST 1: SETUP TEST ENVIRONMENT ==="
worktree_docker blooop/test_wtd git status
echo "✓ Test environment created"

# Verify container exists
docker ps | grep test_worktree_docker-main
echo "✓ Container is running"

# Test 2: Selective prune - should remove only blooop/test_wtd environment
echo "=== TEST 2: SELECTIVE PRUNE TEST ==="
worktree_docker --prune blooop/test_wtd
echo "✓ Selective prune completed"

# Verify specific container is gone (check exact name)
if docker ps --format "table {{.Names}}" | grep "^test_worktree_docker-main$"; then
    echo "✗ Container should have been removed by selective prune"
    exit 1
else
    echo "✓ Container correctly removed by selective prune"
fi

# Verify worktree is gone
if [ -d ~/.worktree_docker/workspaces/blooop/test_wtd/worktree-main ]; then
    echo "✗ Worktree should have been removed by selective prune"
    exit 1
else
    echo "✓ Worktree correctly removed by selective prune"
fi

# Test 3: Set up multiple environments for full prune test
echo "=== TEST 3: SETUP MULTIPLE ENVIRONMENTS ==="
worktree_docker blooop/test_wtd git status
worktree_docker blooop/test_wtd@dev git status 2>/dev/null || worktree_docker blooop/test_wtd@main git status  # Use main if dev doesn't exist
echo "✓ Multiple environments created"

# Test 4: Full prune - should remove everything
echo "=== TEST 4: FULL PRUNE TEST ==="
worktree_docker --prune
echo "✓ Full prune completed"

# Verify worktree_docker-related containers are gone
if docker ps --format "table {{.Names}}" | grep -E "(test_worktree_docker|worktree_docker-)"; then
    echo "✗ No worktree_docker containers should exist after full prune"
    exit 1
else
    echo "✓ All worktree_docker containers correctly removed by full prune"
fi

if [ -d ~/.worktree_docker ]; then
    echo "✗ .worktree_docker directory should have been removed by full prune"
    exit 1
else
    echo "✓ .worktree_docker directory correctly removed by full prune"
fi

echo "=== ALL PRUNE TESTS PASSED ==="