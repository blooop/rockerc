#!/usr/bin/env bash
set -e

rm -rf ~/.renv

echo "=== BASIC CONTAINER LIFECYCLE TEST ==="
echo "Testing core container state transitions"

# Clean up any existing test containers
echo "=== INITIAL CLEANUP ==="
docker container stop test_renv-main
docker rm -f test_renv-main 
echo "Cleaned up existing test containers"

# Test 1: Fresh start - no container exists
echo "=== TEST 1: FRESH START ==="
renv blooop/test_renv git status
echo "✓ Fresh container test completed"

#stop existing container and run renv again (should start a new one)
docker container stop test_renv-main
renv blooop/test_renv git status


#delete container and run renv again (should start a new one)
docker rm -f test_renv-main 
renv blooop/test_renv git status