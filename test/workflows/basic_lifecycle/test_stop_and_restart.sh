#!/usr/bin/env bash
set -e
cd /tmp

echo "=== TEST 2: STOP AND RESTART ==="
docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
renv blooop/test_renv git status
echo "✓ Stop and restart test completed"
