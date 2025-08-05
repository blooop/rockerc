#!/usr/bin/env bash
set -e
cd /tmp

# #worktree_docker is set up in this repo

echo "Running: wtd blooop/test_wtd \"bash -c 'git status; pwd; ls -l'\"" to confirm that multi step commands work as expected
wtd blooop/test_wtd "bash -c 'git status; pwd; ls -l'"



