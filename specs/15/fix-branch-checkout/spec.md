# Fix Branch Checkout

## Problem
When running `renv owner/repo@branch`, if a local copy doesn't exist, it creates a new local branch from the default branch instead of checking out the existing remote branch.

## Expected Behavior
- If branch exists locally: checkout directly (no fetch/pull)
- If branch doesn't exist locally but exists on remote: fetch cache and checkout remote tracking branch
- If branch doesn't exist anywhere: create new branch from default

## Implementation
Modify `setup_branch_copy()` to check for remote tracking branches after copying cache, and checkout from origin if the branch exists remotely.
