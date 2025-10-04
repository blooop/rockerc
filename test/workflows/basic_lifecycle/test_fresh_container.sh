#!/usr/bin/env bash
set -e
rm -rf ~/renv
cd /tmp

echo "=== TEST 1: FRESH START ==="
renv blooop/test_renv git status
echo "✓ Fresh container test completed"
