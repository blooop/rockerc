#!/usr/bin/env bash
set -e
cd /tmp

echo "=== TEST 3: DELETE AND RESTART ==="
docker rm -f test_renv-main 2>/dev/null || echo "Container test_renv-main not found"
renv blooop/test_renv git status
echo "✓ Delete and restart test completed"
