#!/usr/bin/env bash
set -e
rm -rf ~/renv
cd /tmp

echo "=== BASIC CONTAINER LIFECYCLE TEST ==="
echo "Testing core container state transitions"

# Clean up any existing test containers
echo "=== INITIAL CLEANUP ==="
docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
docker rm -f test_renv-main 2>/dev/null || echo "Container test_renv-main not found"
echo "Cleaned up existing test containers"

# Test 1: Fresh start - no container exists
echo "=== TEST 1: FRESH START ==="
renv blooop/test_renv git status
echo "✓ Fresh container test completed"

# # Test 2: Stop existing container and run renv again (should start a new one)
# echo "=== TEST 2: STOP AND RESTART ==="
# docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
# renv blooop/test_renv git status
# echo "✓ Stop and restart test completed"

# # Test 3: Delete container and run renv again (should start a new one)
# echo "=== TEST 3: DELETE AND RESTART ==="
# docker rm -f test_renv-main 2>/dev/null || echo "Container test_renv-main not found"
# renv blooop/test_renv git status
# echo "✓ Delete and restart test completed"

# # Test 4: Test force rebuild after worktree corruption
# echo "=== TEST 4: FORCE REBUILD AFTER CORRUPTION ==="
# # Stop the container first to avoid permission issues
# docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
# # Use docker to change permissions first, then remove
# docker run --rm -v ~/renv:/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
# rm -rf ~/renv
# echo "Testing force rebuild after renv dir deletion..."
# renv --force blooop/test_renv git status
# echo "✓ Force rebuild test completed"

# # Test 5: Test container breakout detection - delete renv dir while container running
# echo "=== TEST 5: CONTAINER BREAKOUT DETECTION ==="
# # First create a fresh container
# docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
# docker rm -f test_renv-main 2>/dev/null || echo "Container test_renv-main not found"
# docker run --rm -v ~/renv:/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
# rm -rf ~/renv
# # Start fresh container
# renv blooop/test_renv echo "Container started successfully"
# # Now delete renv directory while container is running
# docker run --rm -v ~/renv:/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
# rm -rf ~/renv
# echo "Testing renv after deleting directory with running container..."
# # This should detect the issue and fix it
# renv blooop/test_renv git status
# echo "✓ Container breakout detection test completed"

# echo "✓ Basic lifecycle test completed successfully"
