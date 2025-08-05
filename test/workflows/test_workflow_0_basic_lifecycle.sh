#!/usr/bin/env bash
set -e

rm -rf ~/.wtd

echo "=== BASIC CONTAINER LIFECYCLE TEST ==="
echo "Testing core container state transitions"

# Clean up any existing test containers
echo "=== INITIAL CLEANUP ==="
docker container stop test_wtd-main
docker rm -f test_wtd-main 
echo "Cleaned up existing test containers"

# Test 1: Fresh start - no container exists
echo "=== TEST 1: FRESH START ==="
wtd blooop/test_wtd git status
echo "✓ Fresh container test completed"

#stop existing container and run wtd again (should start a new one)
docker container stop test_wtd-main
wtd blooop/test_wtd git status


#delete container and run wtd again (should start a new one)
docker rm -f test_wtd-main 
wtd blooop/test_wtd git status