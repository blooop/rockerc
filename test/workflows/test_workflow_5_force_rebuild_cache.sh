#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv



echo "Running: renv --force blooop/test_renv date to force a rebuild"
renv --force blooop/test_renv date

echo "Running: renv --nocache blooop/test_renv date to force a rebuild without using cache (this should take longer than the previous command)"
renv --nocache blooop/test_renv date


echo "Running: renv blooop/test_renv date should finish faster because the cache is getting used"
renv blooop/test_renv date