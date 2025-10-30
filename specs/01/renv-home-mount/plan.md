# Implementation Plan: Mount renv projects to user home directory

## Current State Analysis

### Problem Details
1. The `cwd` extension in deps_rocker was updated to mount to `~/project_name`
2. However, renv.py explicitly overrides this by passing `mount_target=f"/{repo_spec.repo}"` to `prepare_launch_plan()`
3. This happens in two places in renv.py:
   - Line 1131: VSCode mode
   - Line 1262: Terminal mode

### Code Flow
```
renv.manage_container()
  ├─> prepare_launch_plan(mount_target=f"/{repo_spec.repo}")  # explicit override
  ├─> core.ensure_volume_binding(mount_target=...)
  └─> Docker runs with -v /host/path:/{repo}:Z
```

## Solution

### Step 1: Remove mount_target override in renv.py
Remove or set to None the `mount_target` parameter in both calls to `prepare_launch_plan()`:
- Line ~1131 (VSCode mode)
- Line ~1262 (Terminal mode)

This allows the default behavior of mounting to `/workspaces/{container_name}` to be used, which the cwd extension will then override to use `~/project_name`.

Wait - actually looking more carefully at the code:

The issue is more subtle. The `mount_target` parameter controls where the volume is mounted. Currently:
- renv sets: `mount_target = f"/{repo_spec.repo}"`
- This makes core.py mount to `/{repo}` directly
- But we want it to mount to `~/repo` instead

### Revised Solution

The correct approach is to:
1. Keep using `mount_target` but change it to use the home directory path
2. Need to get the container's home directory - this comes from the user extension
3. However, we don't have easy access to that in renv at this point

**Better approach**: Don't specify mount_target at all, let it default to `/workspaces/{container_name}`, then rely on the cwd extension being enabled to handle the proper mounting.

But wait - renv removes the cwd extension! Line 719:
```python
# Remove cwd extension - we use explicit volume mounts to /{repo} instead
if "cwd" in config["args"]:
    config["args"].remove("cwd")
```

### Actual Solution

1. **Stop removing the cwd extension** - Remove lines that strip out cwd from config["args"]
2. **Remove mount_target override** - Don't pass mount_target parameter to prepare_launch_plan()
3. **Remove explicit volume mounting** - The cwd extension will handle this
4. **Update working directory references** - Change from `/{repo}` to use cwd-based path

Actually, this is tricky because renv has special requirements:
- It needs to mount the branch directory
- It may need extra volume for .git when using subfolders
- The container name is not the same as the folder name (uses repo.branch format)

### Final Solution

The cleanest approach is:
1. **Re-enable cwd extension** - Don't remove it from args
2. **Don't pass explicit mount_target** - Let cwd extension determine the path
3. **Update workdir references** - The working directory should match where cwd mounts
4. **Keep the existing volume mount logic** - But specify mount to `~/repo` instead of `/{repo}`

Looking at the cwd extension code, it:
- Gets `user_home_dir` from cliargs (set by user extension)
- Mounts current directory to `{user_home_dir}/{project_name}`
- Sets working directory to that path

But renv changes directory before calling rocker, so cwd extension would pick up the wrong directory.

### Actual Working Solution

After careful analysis, the correct approach is:

1. **Use cwd extension properly** - Don't remove it, but don't rely on auto-detection
2. **Pass correct mount_target** - Use `~/repo` instead of `/{repo}`
3. **Let prepare_launch_plan handle mounting** - It calls ensure_volume_binding with our mount_target

The key insight: `mount_target` parameter in prepare_launch_plan is exactly for this purpose - to customize where the volume gets mounted. We just need to change it from `/{repo}` to `~/repo`.

But `~` gets expanded to the host user's home, not container user's home. We need the actual container home path.

Looking at the user extension in rocker, it creates a user with a home directory. The home path is typically `/home/{username}`. But we don't know the username at this point in renv.

**Solution**: Use a special mount_target syntax that core.py/rocker understands, or:

Actually, the simplest solution:
1. Keep the explicit volume mount to `/{repo}` as-is for compatibility
2. Add a symbolic link or change working directory expectations
3. OR: Accept that renv uses `/{repo}` while rockerc uses `~/project`

After all this analysis, let me reconsider the original request. The user said "I updated the cwd extension to mount to home directory instead of root directory, but when I use renv it has extra logic related to folder mounting so it's not working properly."

The key issue: The cwd extension change isn't being used by renv because renv explicitly specifies mount locations.

### Final Final Solution

The path forward:
1. **Don't remove cwd from args** - Let it be present
2. **Don't pass mount_target to prepare_launch_plan** - Use default (which cwd will override)
3. **Don't explicitly mount volumes** - Let cwd extension handle it
4. **BUT** - We need to handle the extra_volumes for .git in subfolder case

Actually, reviewing the code again more carefully:

The `prepare_launch_plan()` in core.py calls `ensure_volume_binding()` which adds a volume mount. The cwd extension in deps_rocker ALSO adds volume mounts. These would conflict or duplicate.

The real issue is that renv and rockerc have fundamentally different approaches:
- rockerc relies on extensions (like cwd) to set up mounts
- renv needs precise control over what gets mounted (branch dir, not cwd, plus .git binding)

**Pragmatic Solution**:

Keep renv's explicit mounting logic, but change the target from `/{repo}` to a home-based path:

1. Get container user info (username from cliargs or config)
2. Use `/home/{username}/{repo}` as mount target instead of `/{repo}`
3. Update all working directory references to match

This requires knowing the username. Looking at the config building in renv, we have access to the full args_dict which should have user info.

## Implementation Steps

1. **Modify renv.py:build_rocker_config()** - Extract or determine container username
2. **Modify renv.py:manage_container()** - Use `/home/{username}/{repo}` for mount_target
3. **Update workdir references** - Change from `/{repo}` to `/home/{username}/{repo}`
4. **Test with real renv environment** - Ensure backwards compatibility

## Testing Plan

1. Create test repo with renv
2. Verify mount location is in home directory
3. Verify VSCode opens correct location
4. Verify git operations work
5. Verify subfolder mode works (.git binding)
6. Run existing test suite
