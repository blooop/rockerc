#!/usr/bin/env bash
set -e
cd /tmp

# Test --nocache flag which ignores Docker layer cache
echo "Running: renv --nocache blooop/test_renv pwd"
renv --nocache blooop/test_renv pwd
echo "✓ No-cache rebuild test completed"
