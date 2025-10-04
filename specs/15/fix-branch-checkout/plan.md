# Implementation Plan

## Changes to renv.py


1. Remove `branch_exists` and `remote_branch_exists` helpers.
2. Add `git_ref_exists(repo_dir, ref)` helper using `git rev-parse --verify`.
3. In `setup_branch_copy()`, after copying cache:
   - Check for local and remote branch existence using `git_ref_exists`.
   - Build a single `git checkout` command:
     - If local: `git checkout <branch>`
     - If remote: `git checkout -b <branch> origin/<branch>`
     - If neither: `git checkout -b <branch> origin/<default>`
   - Run checkout and handle errors (log and raise if fails).
4. Run `pixi run ci` to ensure all tests pass.

## Testing
- Run `pixi run ci` to ensure all tests pass
