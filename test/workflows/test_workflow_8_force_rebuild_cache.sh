#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

echo "Running: renv blooop/test_renv@main -f"
renv blooop/test_renv@main -f

echo "Running: renv blooop/test_renv@main --nocache"
renv blooop/test_renv@main --nocache