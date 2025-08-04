#!/usr/bin/env bash
set -e
cd /tmp


echo "Running: wtd blooop/test_worktree_docker touch persistent.txt to confirm that persistent files work as expected"
wtd blooop/test_worktree_docker touch persistent.txt

echo "Running: wtd blooop/test_worktree_docker ls to confirm that persistent files are present"
wtd blooop/test_worktree_docker ls