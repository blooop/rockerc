#!/usr/bin/env bash
set -e

echo "Running: renv prune to clean up all docker containers, images, and folders"
renv --prune

echo "Running: renv blooop/test_renv and confirming the git status works as expected"
renv blooop/test_renv git status

echo "Should enter a clean workspace, with no dirty changes"