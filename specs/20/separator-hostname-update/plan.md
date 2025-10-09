# Implementation Plan

## Phase 1: Update Container Name Generation (COMPLETED)
1. Modify `get_container_name()` in `rockerc/renv.py`
   - Change `-b-` separator to `.`
   - Update function documentation

## Phase 2: Update Hostname Generation (COMPLETED)
1. Modify hostname assignment in `build_rocker_config()`
   - Set hostname to just repo name instead of full container name
   - Add new helper function to generate hostname separately

## Phase 3: Update Mount Path Logic
1. Change container mount path generation
   - Replace `/workspaces/{container_name}` with `/home/{user}/{repo}`
   - Update in `manage_container()` function around lines 1088-1099
   - Update working directory references around lines 1337-1338
   - Need to determine username (can use USER env var or default to container user)

2. Update .git bind mount for subfolders
   - Change from `/workspaces/{container_name}/.git` to `/home/{user}/{repo}/.git`
   - Keep subfolder mounting logic but update paths

## Phase 4: Disable CWD Extension for renv
1. Modify `build_rocker_config()` in `rockerc/renv.py`
   - Remove "cwd" from args list after all configs are merged (around line 793-795)
   - Add comment explaining why cwd is disabled for renv
   - This prevents the rockerc-cwd extension from interfering with renv's mount logic

## Phase 5: Update Tests
1. Update all test cases in `test/test_renv.py`
   - Container name expectations: `test_renv.main` instead of `test_renv-b-main` (DONE)
   - Hostname expectations: `test_renv` instead of `test_renv-b-main` (DONE)
   - Subfolder test expectations: `test_renv.main-sub-src` format (DONE)
   - Mount path expectations: `/home/{user}/{repo}` instead of `/workspaces/{container_name}`
   - Working directory expectations in tests

## Phase 6: Validation
1. Run CI to ensure all tests pass
2. Verify no regressions in functionality
3. Test edge cases with special characters in branch names
4. Test subfolder mounting still works correctly
5. Manual testing of prompt display

## Edge Cases to Consider
- Branch names with slashes (already handled by replacement with dashes)
- Subfolder paths with special characters
- Hostname length limits for Docker containers
- Backward compatibility considerations
- Username determination in containers (USER env var, default to current user)
- Handling of existing containers with old mount paths