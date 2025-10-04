# Fix Branch Checkout

## Problem
When running `renv owner/repo@branch`, if a local copy doesn't exist, it creates a new local branch from the default branch instead of checking out the existing remote branch.

## Expected Behavior
- If branch exists locally: checkout directly (no fetch/pull)
- If branch doesn't exist locally but exists on remote: fetch cache and checkout remote tracking branch
- If branch doesn't exist anywhere: create new branch from default


## Implementation (Updated per review)
- Remove custom `branch_exists` and `remote_branch_exists` helpers.
- Add a single `git_ref_exists` helper using `git rev-parse --verify` for both local and remote branch checks.
- Collapse all checkout logic in `setup_branch_copy()` to use this helper and a single checkout command.
- Add error handling for failed checkouts (log and raise with clear message).
