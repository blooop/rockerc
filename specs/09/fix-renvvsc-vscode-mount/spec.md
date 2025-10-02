# Fix renvvsc VSCode Mount Path

## Problem
renvvsc fails to attach VSCode to the container, showing "Workspace does not exist" error.

## Root Cause
renv mounts workspace at `/workspace/{repo}-{branch}` but VSCode's `launch_vscode()` expects `/workspaces/{container_name}` (note plural "workspaces").

## Solution
Change renv to mount at `/workspaces/{container_name}` with `:Z` flag to match rockerc's convention exactly.

## Files to Modify
- `rockerc/renv.py`: Update `build_rocker_config()` to use `/workspaces/{container_name}:Z` mount path
