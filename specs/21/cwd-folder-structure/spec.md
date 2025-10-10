## Goal

Fix renvvsc by restructuring the folder layout so that the cwd extension handles all mount path logic, keeping behavior consistent between rockerc, rockervsc, renv, and renvvsc.

Ensure that the folder loaded in the container is always named after the project name `{repo}`, regardless of whether it's accessed via CLI or VSCode.

## Problem

The reverted commit (a836fbe) tried to use custom mount targets and removed the cwd extension for renv. This broke rockervsc because it expected the standard `/workspaces/{container_name}` mount pattern.

Additionally, the previous implementation mounted the repo directory directly to `/workspaces/{container_name}/`, which meant the folder name in the container was `{container_name}` (e.g., `test_renv.main`), not the project name.

## Solution

Instead of customizing mount targets, restructure the folder layout:

**Current:** `/renv/{owner}/{repo}/{repo}-{branch}/`
**New:** `/renv/{owner}/{repo}/{branch}/{repo}/`

This allows us to:
1. cd to `/renv/{owner}/{repo}/{branch}/` (the parent directory)
2. Let the cwd extension mount `/renv/{owner}/{repo}/{branch}/` to `/workspaces/{container_name}/`
3. Inside the container, the project is at `/workspaces/{container_name}/{repo}/` (folder name is always `{repo}`)
4. VSCode and terminal both open `/workspaces/{container_name}/{repo}/`
5. Keep the cwd extension enabled for all modes
6. Maintain consistent behavior across rockerc/rockervsc/renv/renvvsc

## Key Changes

- Modify `get_worktree_dir()` to return `~/renv/{owner}/{repo}/{branch}/{repo}`
- Update `setup_branch_copy()` to create the new folder structure
- Update `build_rocker_config()` to set `target_dir` to parent directory (without subfolder)
- Update `launch_vscode()` in core.py to accept optional folder_path parameter
- Update renv.py to pass `/workspaces/{container_name}/{repo}` to VSCode (without subfolder)
- Update docker exec commands to use `/workspaces/{container_name}/{repo}` as workdir (without subfolder)
- Keep the cwd extension enabled (no changes to extension handling)
- Ensure legacy migrations work correctly
