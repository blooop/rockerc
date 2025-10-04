#!/usr/bin/env bash
set -e

RENV_DIR="${RENV_DIR:-$HOME/renv}"

cd /tmp

docker container stop test_renv-main 2>/dev/null || echo "Container test_renv-main not running"
docker run --rm -v "${RENV_DIR}":/renv ubuntu:22.04 chmod -R 777 /renv 2>/dev/null || echo "No renv directory to chmod"
rm -rf "${RENV_DIR}"
echo "Testing force rebuild after renv dir deletion..."
renv --force blooop/test_renv git status
echo "✓ Force rebuild test completed"
