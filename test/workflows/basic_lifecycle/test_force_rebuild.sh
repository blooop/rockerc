#!/usr/bin/env bash
set -e
cd /tmp

echo "=== TEST 4: FORCE REBUILD AFTER CORRUPTION ==="
docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
docker run --rm -v ~/renv:/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
rm -rf ~/renv
echo "Testing force rebuild after renv dir deletion..."
renv --force blooop/test_renv git status
echo "✓ Force rebuild test completed"
