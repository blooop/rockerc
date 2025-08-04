#!/usr/bin/env bash
set -e

echo "Running: worktree_docker blooop/test_wtd and confirming the working directory is test_worktree_docker to match the name of the git repo"
worktree_docker blooop/test_wtd pwd


