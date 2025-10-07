# Implementation Plan

## Overview
Implement git sparse-checkout to enable isolated subfolder access in renv containers for monorepo development.

## Key Changes

### 1. Modify `setup_branch_copy()` in renv.py
- After copying from cache, detect if `repo_spec.subfolder` is set
- If subfolder is specified:
  - Initialize sparse-checkout: `git sparse-checkout init --cone`
  - Set sparse-checkout pattern: `git sparse-checkout set {subfolder}`
  - This will populate only the specified subfolder in the working tree
- The .git directory remains complete with full history

### 2. Update volume mounting logic
Currently in `build_rocker_config()`:
- Line 526 sets `_renv_target_dir` to `branch_dir / repo_spec.subfolder`
- This changes cwd but still mounts entire branch_dir

Need to modify volume mounting in `manage_container()` or `build_rocker_config()`:
- When subfolder is specified, mount `{branch_dir}/{subfolder}` as the workspace root
- This ensures only the subfolder is visible in the container
- Git operations still work because git can traverse up to find .git directory

### 3. Handle git directory visibility
With sparse-checkout:
- The .git directory stays at the repo root
- Subfolder can access it via parent directory traversal
- Inside container, git commands work normally
- Container user can't see parent folders due to mount isolation

### 4. Update shell completion (optional enhancement)
- Bash completion already supports `#` syntax (line 205-220 handles branch completion after @)
- Could add subfolder completion after # by listing directories in the repo
- This is optional - manual typing of subfolder path works fine

### 5. Test scenarios
- Clone repo with subfolder: `renv owner/repo@branch#folder/subfolder`
- Verify only subfolder visible in container
- Git status, commit, push from within subfolder
- Verify changes appear in parent repo on host

## Implementation Steps
1. Modify `setup_branch_copy()` to enable sparse-checkout when subfolder specified
2. Update volume mount calculation to use subfolder path when present
3. Test with real monorepo
4. Update documentation

## Technical Notes

### Git Sparse-Checkout
```bash
# Initialize cone mode (more efficient)
git sparse-checkout init --cone

# Set paths to include
git sparse-checkout set folder/subfolder

# This creates .git/info/sparse-checkout file
# Working tree now only contains specified folders
```

### Volume Mount Strategy
Current: `{host_path}:/workspaces/{container_name}`
With subfolder: `{host_path}/{subfolder}:/workspaces/{container_name}`

Git still works because:
- .git directory is at repo root (above subfolder)
- Git commands traverse up to find .git
- All metadata available for normal operations

### Isolation Guarantee
- Container mount point only includes subfolder
- User cannot `cd ../` beyond the mount point
- Even if they try, parent folders aren't visible
- This provides true isolation for monorepo development
