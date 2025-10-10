## Goal

Fix renvvsc by restructuring the folder layout so that the cwd extension handles all mount path logic, keeping behavior consistent between rockerc, rockervsc, renv, and renvvsc.

## Problem

The reverted commit (a836fbe) tried to use custom mount targets and removed the cwd extension for renv. This broke rockervsc because it expected the standard `/workspaces/{container_name}` mount pattern.

## Solution

Instead of customizing mount targets, restructure the folder layout:

**Current:** `/renv/{owner}/{repo}/{repo}-{branch}/`
**New:** `/renv/{owner}/{repo}/{branch}/{repo}/`

This allows us to:
1. cd to `/renv/{owner}/{repo}/{branch}/` (the parent directory)
2. Let the cwd extension detect we're in a directory containing `{repo}/`
3. Keep the cwd extension enabled for all modes
4. Maintain consistent behavior across rockerc/rockervsc/renv/renvvsc

## Key Changes

- Modify `get_worktree_dir()` to return `~/renv/{owner}/{repo}/{branch}/{repo}`
- Update `setup_branch_copy()` to create the new folder structure
- Keep the cwd extension enabled (no changes to extension handling)
- Ensure legacy migrations work correctly
