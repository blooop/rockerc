#!/usr/bin/env bash
set -e
cd /tmp

# #rockerc is set up in this repo

echo "Running: renv blooop/test_renv \"bash -c 'git status; pwd; ls -l'\""
renv blooop/test_renv "bash -c 'git status; pwd; ls -l'"



