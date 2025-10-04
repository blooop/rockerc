#!/usr/bin/env bash
set -e
cd /tmp

echo "Running: renv blooop/test_renv to confirm git status is clean (no staged deletions or untracked files)"

# First clean up any untracked files from previous tests
echo "Cleaning up any leftover files from previous tests..."
renv blooop/test_renv -- git reset --hard HEAD 2>/dev/null || true
renv blooop/test_renv -- git clean -fd 2>/dev/null || true

# Run a command that outputs a marker before and after git status to isolate the git output
status_output=$(renv blooop/test_renv -- git status --porcelain 2>/dev/null)

# Extract only porcelain status lines (skip renv logging noise)
git_output=$(echo "$status_output" | grep -E '^(\?\?| [MADRCU?!]|[MADRCU?!] ) ' || true)

# Check if there are any changes (git status --porcelain should be empty for clean repo)
if [ -n "$git_output" ]; then
    echo "ERROR: Git status is not clean. Output:"
    echo "$git_output"
    echo "Full git status:"
    renv blooop/test_renv -- git status 2>/dev/null
    exit 1
fi

echo "SUCCESS: Git status is clean"
