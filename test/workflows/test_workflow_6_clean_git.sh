#!/usr/bin/env bash
set -e
cd /tmp

echo "Running: renv blooop/test_renv to confirm git status is clean (no staged deletions or untracked files)"

# First clean up any untracked files from previous tests
echo "Cleaning up any leftover files from previous tests..."
renv blooop/test_renv "git reset --hard HEAD; git clean -fd" 2>/dev/null || true

# Run a command that outputs a marker before and after git status to isolate the git output
full_output=$(renv blooop/test_renv "echo '=== GIT_STATUS_START ==='; git status --porcelain; echo '=== GIT_STATUS_END ==='" 2>/dev/null)

# Extract just the git status output between the markers
git_output=$(echo "$full_output" | sed -n '/=== GIT_STATUS_START ===/,/=== GIT_STATUS_END ===/p' | sed '1d;$d')

# Check if there are any changes (git status --porcelain should be empty for clean repo)
if [ -n "$git_output" ]; then
    echo "ERROR: Git status is not clean. Output:"
    echo "$git_output"
    echo "Full git status:"
    renv blooop/test_renv git status 2>/dev/null
    exit 1
fi

echo "SUCCESS: Git status is clean"
