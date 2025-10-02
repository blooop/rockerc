#!/usr/bin/env bash
set -e
cd /tmp

# #rockerc is set up in this repo

echo "Running: renv blooop/test_renv git status; pwd; ls -l to confirm commands run inside container"
renv blooop/test_renv -- git status
renv blooop/test_renv -- pwd
renv blooop/test_renv -- ls -l
