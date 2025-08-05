#!/bin/bash

# Test workflow for uv extension using generic extension test runner
# This test verifies that the uv Python package manager extension loads and works correctly

set -e

echo "=== TEST: UV EXTENSION (using generic test runner) ==="

# Use the generic extension test runner
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/../extension_test_runner.py" uv