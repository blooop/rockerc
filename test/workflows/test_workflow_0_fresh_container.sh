#!/usr/bin/env bash
set -e

RENV_DIR="${RENV_DIR:-$HOME/renv}"
rm -rf "${RENV_DIR}"
# Remove all containers with test_renv in the name
docker ps -a --format '{{.Names}}' | grep 'test_renv' | xargs -r docker rm -f
cd /tmp

renv blooop/test_renv git status
echo "✓ Fresh container test completed"
