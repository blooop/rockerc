#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

# Clean up test container for fresh start
echo "=== CLEANING TEST ENVIRONMENT ==="
docker rm -f test_renv-main >/dev/null 2>&1 || true

# Test --nocache flag which ignores Docker layer cache
echo "=== NO-CACHE REBUILD TEST ==="
echo "Running: renv --nocache blooop/test_renv date"
renv --nocache blooop/test_renv date
echo "✓ No-cache rebuild test completed"
