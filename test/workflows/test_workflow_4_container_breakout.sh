#!/usr/bin/env bash
set -e

RENV_DIR="${RENV_DIR:-$HOME/renv}"

cd /tmp

docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
docker rm -f test_renv-main 2>/dev/null || echo "Container test_renv-main not found"
docker run --rm -v "${RENV_DIR}":/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
rm -rf "${RENV_DIR}"
renv blooop/test_renv echo "Container started successfully"
docker run --rm -v "${RENV_DIR}":/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
rm -rf "${RENV_DIR}"
echo "Testing renv after deleting directory with running container..."
renv blooop/test_renv git status
echo "✓ Container breakout detection test completed"
