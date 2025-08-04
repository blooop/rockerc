#!/usr/bin/env bash
set -e
cd /tmp

# #rockerc is set up in this repo

echo "Running: renv blooop/test_wtd \"bash -c 'git status; pwd; ls -l'\"" to confirm that multi step commands work as expected
renv blooop/test_wtd "bash -c 'git status; pwd; ls -l'"



