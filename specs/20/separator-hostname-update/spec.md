# Separator, Hostname, and Mount Path Update

## Summary
Update the separator between repo name and branch from `-b-` to `.`, modify hostname generation to only include the repo name without branch, and change renv mounting to use home directory root instead of `/workspaces`.

## Changes Required

### Separator Update
- Change separator from `-b-` to `.` in container name generation
- Update `get_container_name()` function in `rockerc/renv.py`

### Hostname Simplification
- Container hostname should only be the repo name, not include branch
- Update hostname assignment in `build_rocker_config()`

### Mount Path Changes
- Mount repositories at home directory root: `/home/{user}/{repo}` instead of `/workspaces/{container_name}`
- Remove branch suffix from container directory name (e.g., `/home/ags/bencher` instead of `/workspaces/bencher.main`)
- For subfolders: mount at `/home/{user}/{repo}` with subfolder content
- Update working directory references throughout container management code

### CWD Extension Handling
- Automatically disable the `cwd` extension when using renv
- Prevent conflicts with renv's custom folder mounting logic
- Ensure cwd extension is removed from args before passing to rocker

### Test Updates
- Update all test expectations to use new separator format
- Update hostname test expectations
- Update mount path expectations in tests

## Expected Behavior
- Container name: `repo.branch` instead of `repo-b-branch`
- Hostname: `repo` instead of `repo-b-branch`
- Subfolder suffix remains: `repo.branch-sub-subfolder`
- Prompt example: `ags@bencher:bencher$` instead of `ags@bencher:/workspaces/bencher.main$`
- Mount at: `/home/{user}/{repo}` instead of `/workspaces/{container_name}`
- Subfolder mounts: `/home/{user}/{repo}` with `.git` bind mount still at appropriate location