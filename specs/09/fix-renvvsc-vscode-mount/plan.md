# Implementation Plan: Fix renvvsc VSCode Mount Path

## Current Behavior
1. renv's `build_rocker_config()` creates volume mount: `{branch_dir}:/workspace/{repo}-{branch}`
2. VSCode's `launch_vscode()` expects workspace at: `/workspaces/{container_name}`
3. Path mismatch causes "Workspace does not exist" error

## Implementation Steps

### 1. Update renv.py mount path
In `build_rocker_config()` function (around line 450):

**Current:**
```python
docker_branch_mount = f"/workspace/{repo_spec.repo}-{safe_branch}"
```

**New:**
```python
docker_branch_mount = f"/workspaces/{container_name}"
```

This aligns with rockerc's `ensure_volume_binding()` which uses `/workspaces/{container_name}`.

### 2. Verify consistency
- Container name is already set via `config["name"] = container_name`
- VSCode URI uses same container name: `vscode-remote://attached-container+{hex}/workspaces/{container_name}`
- Mount path will now match VSCode's expectation

## Testing
- Run `renvvsc owner/repo@branch`
- VSCode should attach to `/workspaces/{container_name}` successfully
- No "Workspace does not exist" error
