#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

#rockerc not set up in this repo
echo "Running: renv osrf/rocker"
renv osrf/rocker pwd; git status

#rockerc is set up in this repo
echo "Running: renv blooop/manifest_rocker@renv_test"
renv blooop/manifest_rocker@renv_test pwd; git status

