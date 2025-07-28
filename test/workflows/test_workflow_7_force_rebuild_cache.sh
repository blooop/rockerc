#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

echo "Running: renv blooop/manifest_rocker@main -f"
renv blooop/manifest_rocker@main -f

echo "Running: renv blooop/manifest_rocker@main --nocache"
renv blooop/manifest_rocker@main --nocache