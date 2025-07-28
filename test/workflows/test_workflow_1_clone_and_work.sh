#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

#rockerc not set up in this repo
echo "Running: renv osrf/rocker and confirm that we are at the root of the mounted worktree and that git status prints a result"
renv osrf/rocker pwd; git status

#rockerc is set up in this repo
echo "Running: renv blooop/manifest_rocker@renv_test and confirming the same works for a repo which has a rockerc.yaml in it"
renv blooop/manifest_rocker@renv_test pwd; git status

