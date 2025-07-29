#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv



echo "Running: renv blooop/test_renv -f to force a rebuild"
renv blooop/test_renv -f date

echo "Running: renv blooop/test_renv --nocache to force a rebuild without using cache (this should take longer than the previous command)"
renv blooop/test_renv --nocache date


echo "Running: renv bloop/test_renv date should finish faster because the cache is getting used"
renv bloop/test_renv date