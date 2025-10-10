#!/usr/bin/env bash
set -e

echo "Cleaning up test containers and directories..."

# Remove all containers with test_renv in the name
echo "Removing test_renv containers..."
docker ps -a --format '{{.Names}}' | grep 'test_renv' | xargs -r docker rm -f || true

# Clean up RENV_DIR
RENV_DIR="${RENV_DIR:-$HOME/renv}"
if [ -d "${RENV_DIR}" ]; then
    echo "Removing ${RENV_DIR}..."
    rm -rf "${RENV_DIR}"
fi

echo "✓ Cleanup completed"
