# Implementation Plan: Multi-Copy Repo with Cache

## Overview
Replace worktree-based approach with simpler multi-copy approach using a cached repo.

## Changes Required

### 1. Update Repository Setup Functions

**`setup_cache_repo(repo_spec)` (replaces `setup_bare_repo`)**
- Clone full repo (not bare) to `~/renv/{owner}/{repo}-cache` if doesn't exist
- Otherwise, fetch all updates in cache
- Return path to cache directory

**`setup_branch_copy(repo_spec)` (replaces `setup_worktree`)**
- Ensure cache exists by calling `setup_cache_repo()`
- Target path: `~/renv/{owner}/{repo}-{branch}`
- If target doesn't exist:
  - Copy entire cache directory to target
  - Checkout the requested branch (create if needed)
- If target exists:
  - Fetch and pull latest changes for the branch
- Return path to branch copy directory

### 2. Update Path Functions

**`get_repo_dir(repo_spec)`**
- Return `~/renv/{owner}/{repo}-cache` (cache directory)

**`get_worktree_dir(repo_spec)` (rename to `get_branch_dir`)**
- Return `~/renv/{owner}/{repo}-{branch}` (branch copy directory)
- Keep old name for now for compatibility, or rename throughout

### 3. Simplify Volume Mounts

**`build_rocker_config()`**
- Remove bare repo mount (no longer needed)
- Remove metadata mount (no longer needed)
- Only mount: `{branch_dir}:/workspace/{repo}-{branch}`
- Simplify structure - only one mount needed

### 4. Remove Worktree-Specific Logic

**`setup_branch_copy()`**
- Remove `.git` file rewriting logic
- Remove relative path conversion
- Remove worktree-specific git commands

**`build_rocker_config()`**
- Remove complex mount structure
- Remove worktree metadata handling

### 5. Update Helper Functions

**`get_available_branches()`**
- Update to work with cache directory structure
- Should work without changes since cache is a full repo

**`branch_exists()`**
- Should work without changes

## Testing Strategy

1. Test cache creation on first run
2. Test cache fetch on subsequent runs
3. Test branch copy creation
4. Test branch copy updates
5. Test with multiple branches
6. Test VSCode integration (renvvsc)
7. Test host git commands work in branch directories
8. Verify extension table still renders correctly

## Migration Notes

- Existing worktree-based setups will need cleanup
- Old structure: `~/renv/{owner}/{repo}/` (bare) and `~/renv/{owner}/{repo}-{branch}/` (worktree)
- New structure: `~/renv/{owner}/{repo}-cache/` and `~/renv/{owner}/{repo}-{branch}/` (full copies)
- Consider adding cleanup command or automatic migration

## Benefits

- Simpler code (remove ~50 lines of worktree-specific logic)
- Better tool compatibility (standard .git directories)
- Easier debugging (standard git structure)
- No path translation needed
