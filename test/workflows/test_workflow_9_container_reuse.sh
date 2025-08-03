#!/usr/bin/env bash
set -e

echo "=== CONTAINER REUSE TEST ==="
echo "Testing that renv reuses existing containers instead of recreating them"

# Clean up any existing test containers and cache
echo "=== INITIAL CLEANUP ==="
rm -rf ~/.renv || true
docker container stop test_renv-main 2>/dev/null || true
docker rm -f test_renv-main 2>/dev/null || true
echo "Cleaned up existing test environment"

# Test 1: Create initial environment
echo "=== TEST 1: CREATE INITIAL ENVIRONMENT ==="
renv blooop/test_renv pwd
echo "✓ Initial environment created"

# Get the container ID for later comparison
CONTAINER_ID_1=$(docker ps --filter "name=test_renv-main" --format "{{.ID}}")
echo "Initial container ID: $CONTAINER_ID_1"

# Test 2: Run another command - should reuse the same container
echo "=== TEST 2: TEST CONTAINER REUSE ==="
renv blooop/test_renv pwd
echo "✓ Second command executed"

# Get the container ID again
CONTAINER_ID_2=$(docker ps --filter "name=test_renv-main" --format "{{.ID}}")
echo "Second container ID: $CONTAINER_ID_2"

# Verify it's the same container
if [ "$CONTAINER_ID_1" = "$CONTAINER_ID_2" ]; then
    echo "✓ Container was reused (same ID: $CONTAINER_ID_1)"
else
    echo "✗ Container was recreated (different IDs: $CONTAINER_ID_1 vs $CONTAINER_ID_2)"
    exit 1
fi

# Test 3: Stop the container manually, then run renv again - should recreate
echo "=== TEST 3: TEST CONTAINER RECREATION AFTER STOP ==="
docker stop test_renv-main
echo "Manually stopped container"

renv blooop/test_renv pwd
echo "✓ Command executed after manual stop"

# Get the container ID after recreation
CONTAINER_ID_3=$(docker ps --filter "name=test_renv-main" --format "{{.ID}}")
echo "Third container ID: $CONTAINER_ID_3"

# Verify it's a different container (recreated)
if [ "$CONTAINER_ID_1" != "$CONTAINER_ID_3" ]; then
    echo "✓ Container was correctly recreated after being stopped (new ID: $CONTAINER_ID_3)"
else
    echo "✗ Container should have been recreated but has same ID: $CONTAINER_ID_3"
    exit 1
fi

# Test 4: Run another command - should reuse the new container
echo "=== TEST 4: TEST REUSE OF RECREATED CONTAINER ==="
renv blooop/test_renv pwd
echo "✓ Command executed on recreated container"

# Get the container ID again
CONTAINER_ID_4=$(docker ps --filter "name=test_renv-main" --format "{{.ID}}")
echo "Fourth container ID: $CONTAINER_ID_4"

# Verify it's the same as the recreated one
if [ "$CONTAINER_ID_3" = "$CONTAINER_ID_4" ]; then
    echo "✓ Recreated container was reused (same ID: $CONTAINER_ID_3)"
else
    echo "✗ Recreated container should have been reused but was different (IDs: $CONTAINER_ID_3 vs $CONTAINER_ID_4)"
    exit 1
fi

echo "=== ALL CONTAINER REUSE TESTS PASSED ==="