#!/usr/bin/env bash
set -e

echo "Running: worktree_docker prune to clean up all docker containers, images, and folders"
worktree_docker --prune

echo "Running: worktree_docker blooop/test_worktree_docker and confirming the git status works as expected"
worktree_docker blooop/test_worktree_docker git status

echo "Should enter a clean workspace, with no dirty changes"