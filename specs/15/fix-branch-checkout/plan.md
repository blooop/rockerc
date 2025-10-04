# Implementation Plan

## Changes to renv.py

1. Add helper function to check if remote tracking branch exists
2. Modify `setup_branch_copy()` logic:
   - When branch dir doesn't exist: copy cache, then check if branch exists remotely
   - If exists remotely: `git checkout -b <branch> origin/<branch>`
   - If doesn't exist remotely: create from default branch as before
   - When branch dir exists: keep current behavior (just fetch and pull)

## Testing
- Run `pixi run ci` to ensure all tests pass
