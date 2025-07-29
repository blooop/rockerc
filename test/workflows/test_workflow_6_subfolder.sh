#!/usr/bin/env bash
set -e
cd /tmp

# Test Workflow 6: Subfolder Support
echo "Testing: Clone repo and start in specific subfolder"
renv blooop/test_renv@main#src git status

echo "Testing: Verify working directory is the subfolder"
renv blooop/test_renv@main#src pwd