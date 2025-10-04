#!/usr/bin/env bash
set -e

cd /tmp

echo "Running: renv blooop/test_renv git status; pwd; ls -l to confirm commands run inside container"
renv blooop/test_renv -- pwd ; ls -l
