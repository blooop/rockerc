# Mount renv projects to user home directory

## Problem
Currently, renv mounts project folders to `/{repo}` at the container root. The cwd extension was updated to mount to the container's home directory (`~/project_name`), but renv has custom logic that bypasses this behavior by explicitly setting `mount_target` to `/{repo}`.

## Goal
Update renv to mount project folders to `~/project_name` instead of `/{repo}`, consistent with the cwd extension's new default behavior.

## Implementation
1. Remove explicit `mount_target` override in renv.py that forces mounting to `/{repo}`
2. Let the cwd extension handle the mount path automatically based on the container's home directory
3. Update working directory references to use the new home-based path
4. Ensure backward compatibility with existing renv environments

## Affected Files
- `rockerc/renv.py`: Remove `mount_target` override in `manage_container()` and `prepare_launch_plan()` calls
- `rockerc/renv_rockerc_template.yaml`: Ensure cwd extension is enabled

## Expected Behavior
- `renv owner/repo@branch` mounts to `~/repo` inside container
- Working directory is `~/repo`
- VS Code opens at `~/repo`
- Git operations work correctly with the new mount location
