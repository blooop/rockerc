# Separator and Hostname Update

## Summary
Update the separator between repo name and branch from `-b-` to `.` and modify hostname generation to only include the repo name without branch.

## Changes Required

### Separator Update
- Change separator from `-b-` to `.` in container name generation
- Update `get_container_name()` function in `rockerc/renv.py`

### Hostname Simplification  
- Container hostname should only be the repo name, not include branch
- Update hostname assignment in `build_rocker_config()`

### Test Updates
- Update all test expectations to use new separator format
- Update hostname test expectations
- Add edge case tests for special characters, dots, dashes, and underscores in repo and branch names
- Add error condition tests for empty strings, special characters, and excessively long names

## Expected Behavior
- Container name: `repo.branch` instead of `repo-b-branch`
- Hostname: `repo` instead of `repo-b-branch`
- Subfolder suffix remains: `repo.branch-sub-subfolder`