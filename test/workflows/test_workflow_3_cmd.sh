#!/usr/bin/env bash
set -e
cd /tmp

# #worktree_docker is set up in this repo

echo "Running: worktree_docker blooop/test_worktree_docker \"bash -c 'git status; pwd; ls -l'\"" to confirm that multi step commands work as expected
worktree_docker blooop/test_worktree_docker "bash -c 'git status; pwd; ls -l'"



