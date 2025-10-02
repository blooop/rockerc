#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

# Clean up test container for fresh start
echo "=== CLEANING TEST ENVIRONMENT ==="
docker rm -f test_renv-main >/dev/null 2>&1 || true
echo "Starting cache performance test..."
echo

# First create a container to establish baseline
echo "=== INITIAL BUILD ==="
echo "Creating initial container for cache testing"
renv blooop/test_renv date
echo

# Force rebuild - removes and recreates container
echo "=== FORCE REBUILD TEST ==="
echo "Running: renv --force blooop/test_renv date to force a rebuild"
renv --force blooop/test_renv date
echo

# Normal run - should reuse existing container (fastest)
echo "=== CONTAINER REUSE TEST ==="
echo "Running: renv blooop/test_renv date should finish fast (reusing existing container)"
renv blooop/test_renv date
echo

# No-cache rebuild - ignores Docker layer cache (if implemented)
echo "=== NO-CACHE REBUILD TEST ==="
echo "Running: renv --nocache blooop/test_renv date"
renv --nocache blooop/test_renv date
echo

echo "Expected: container reuse should be fastest, force rebuild creates new container"
