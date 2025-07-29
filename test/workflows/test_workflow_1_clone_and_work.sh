#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

#rockerc is set up in this repo
echo "Running: renv bloop/manifest_rocker@renv_test and confirming the directory is manifest_rocker"
renv blooop/manifest_rocker@renv_test git status


echo "Running: renv bloop/manifest_rocker@renv_test and confirming the directory is manifest_rocker"
renv blooop/test_renv@osrf_renv_test git status

