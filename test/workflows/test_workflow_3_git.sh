#!/usr/bin/env bash
set -e
cd /tmp

# #rockerc is set up in this repo
# echo "Running: renv bloop/manifest_rocker@renv_test and confirming the directory is manifest_rocker"
# renv blooop/manifest_rocker@renv_test git status


echo "Running: renv bloop/manifest_rocker@renv_test and confirming the directory is manifest_rocker"
renv osrf/rocker@renv_test git status
