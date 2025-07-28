#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

#rockerc is set up in this repo
echo "Running: renv blooop/manifest_rocker@renv_test and confirming the same works for a repo which has a rockerc.yaml in it"
renv blooop/manifest_rocker@renv_test pwd

