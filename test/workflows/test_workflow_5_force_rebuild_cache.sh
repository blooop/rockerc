#!/usr/bin/env bash
set -e
cd /tmp


# Clean up test container for fresh start
echo "=== CLEANING TEST ENVIRONMENT ==="
docker rm -f test_renv-main >/dev/null 2>&1 || true
echo "Starting cache performance test..."
echo

# First create a container to establish baseline
echo "=== INITIAL BUILD ==="
echo "Creating initial container for cache testing"
start_time=$(date +%s)
renv blooop/test_wtd date
end_time=$(date +%s)
initial_time=$((end_time - start_time))
echo "TIMING: Initial build took ${initial_time} seconds"
echo

# Force rebuild - removes and recreates container
echo "=== FORCE REBUILD TEST ==="
echo "Running: renv --rebuild blooop/test_wtd date to force a rebuild"
start_time=$(date +%s)
renv --rebuild blooop/test_wtd date
end_time=$(date +%s)
force_time=$((end_time - start_time))
echo "TIMING: Force rebuild took ${force_time} seconds"
echo

# Normal run - should reuse existing container (fastest)
echo "=== CONTAINER REUSE TEST ==="
echo "Running: renv blooop/test_wtd date should finish fast (reusing existing container)"
start_time=$(date +%s)
renv blooop/test_wtd date
end_time=$(date +%s)
reuse_time=$((end_time - start_time))
echo "TIMING: Container reuse took ${reuse_time} seconds"
echo

# No-cache rebuild - ignores Docker layer cache (if implemented)
echo "=== NO-CACHE REBUILD TEST ==="
echo "Running: renv --nocache blooop/test_wtd date"
start_time=$(date +%s)
renv --nocache blooop/test_wtd date
end_time=$(date +%s)
nocache_time=$((end_time - start_time))
echo "TIMING: No-cache rebuild took ${nocache_time} seconds"
echo

# Print timing summary
echo "=== TIMING SUMMARY ==="
echo "Initial build:      ${initial_time}s"
echo "Force rebuild:      ${force_time}s"  
echo "Container reuse:    ${reuse_time}s"
echo "No-cache rebuild:   ${nocache_time}s"
echo
echo "Expected: container reuse should be fastest, force rebuild creates new container"