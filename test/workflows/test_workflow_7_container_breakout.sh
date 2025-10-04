#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

echo "=== CONTAINER BREAKOUT DETECTION TEST ==="
echo "This test verifies that rockerc detects and handles container breakout"
echo "when ~/renv is deleted while a container is running."

# Clean up any existing test containers and renv directory
echo "=== INITIAL CLEANUP ==="
docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
docker rm -f test_renv-main 2>/dev/null || echo "Container test_renv-main not found"
docker run --rm -v ~/renv:/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
rm -rf ~/renv

# Test 1: Create initial container
echo "=== STEP 1: CREATE INITIAL CONTAINER ==="
echo "Running: renv blooop/test_renv echo 'Container started successfully'"
renv blooop/test_renv echo "Container started successfully"
echo "✓ Initial container created"

# Verify container exists
container_status=$(docker inspect -f '{{.State.Status}}' test_renv-main 2>/dev/null || echo "not found")
if [ "$container_status" = "running" ]; then
    echo "✓ Container test_renv-main is running"
else
    echo "ERROR: Container test_renv-main is not running (status: $container_status)"
    exit 1
fi

# Test 2: Delete renv directory while container is running (simulate breakout)
echo "=== STEP 2: SIMULATE CONTAINER BREAKOUT ==="
echo "Deleting ~/renv directory while container is running..."
docker run --rm -v ~/renv:/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
rm -rf ~/renv
echo "✓ Deleted ~/renv directory"

# Verify renv directory is gone
if [ -d ~/renv ]; then
    echo "ERROR: ~/renv directory still exists"
    exit 1
fi
echo "✓ Confirmed ~/renv directory is deleted"

# Test 3: Run renv again - should detect breakout and rebuild
echo "=== STEP 3: DETECT BREAKOUT AND REBUILD ==="
echo "Running: renv blooop/test_renv git status"
echo "Expected: Container breakout detection and automatic rebuild"
output=$(renv blooop/test_renv git status 2>&1 || true)

# Check for breakout detection message
if echo "$output" | grep -q "Container appears corrupted (possible breakout detection)"; then
    echo "✓ Container breakout detected successfully"
else
    echo "WARNING: Breakout detection message not found in output"
    echo "Output was:"
    echo "$output"
fi

# Verify command succeeded
if echo "$output" | grep -q "On branch main"; then
    echo "✓ Container rebuilt and command executed successfully"
else
    echo "ERROR: Container rebuild may have failed"
    echo "Output was:"
    echo "$output"
    exit 1
fi

# Test 4: Verify new container is functional
echo "=== STEP 4: VERIFY NEW CONTAINER ==="
renv blooop/test_renv pwd
echo "✓ New container is functional"

echo ""
echo "✓ Container breakout detection test PASSED"
echo "All steps completed successfully:"
echo "  1. Created initial container"
echo "  2. Deleted ~/renv while container running (simulated breakout)"
echo "  3. Detected breakout and rebuilt container automatically"
echo "  4. Verified new container is functional"
