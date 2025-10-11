## Goal

Unify workspace and folder loading across rockerc, rockervsc, renv, and renvvsc. Ensure that the folder loaded in the container is always at `/{repo}` at the root of the container, matching how rockerc works, regardless of whether it's accessed via CLI or VSCode.

## Problem

Previous implementation used the cwd extension which mounted to `/workspaces/{container_name}/`, resulting in working directories like `/workspaces/test_renv.main/test_renv`. This was inconsistent with rockerc behavior.

## Solution

Remove the cwd extension and use explicit volume mounts to `/{repo}` at root:

**Host folder structure:** `/renv/{owner}/{repo}/{branch}/{repo}/`

This allows us to:
1. Mount `/renv/{owner}/{repo}/{branch}/{repo}` directly to `/{repo}` in the container
2. Inside the container, the project is always at `/{repo}` (folder name is always `{repo}`)
3. VSCode and terminal both open `/{repo}`
4. Maintain consistent behavior with rockerc (which uses `/{project-name}`)
5. Remove /workspaces/ paths entirely from renv

## Key Changes

- Remove cwd extension from renv config (explicit mounts instead)
- Add custom mount_target parameter support to core.py:
  - Modified `ensure_volume_binding()` to accept optional mount_target
  - Modified `build_rocker_arg_injections()` to pass mount_target
  - Modified `prepare_launch_plan()` to pass mount_target
- Update renv.py to use `mount_target = f"/{repo}"` for all prepare_launch_plan calls
- Update VSCode launch to use `f"/{repo}"` folder path
- Update docker exec commands to use `f"/{repo}"` as workdir
- Update all tests to expect `/{repo}` instead of `/workspaces/{container_name}/{repo}`
