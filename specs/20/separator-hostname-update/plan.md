# Implementation Plan

## Phase 1: Update Container Name Generation
1. Modify `get_container_name()` in `rockerc/renv.py`
   - Change `-b-` separator to `.`
   - Update function documentation
   
## Phase 2: Update Hostname Generation  
1. Modify hostname assignment in `build_rocker_config()`
   - Set hostname to just repo name instead of full container name
   - Add new helper function to generate hostname separately

## Phase 3: Update Tests
1. Update all test cases in `test/test_renv.py`
   - Container name expectations: `test_renv.main` instead of `test_renv-b-main`
   - Hostname expectations: `test_renv` instead of `test_renv-b-main`
   - Subfolder test expectations: `test_renv.main-sub-src` format

## Phase 4: Validation
1. Run CI to ensure all tests pass
2. Verify no regressions in functionality
3. Test edge cases with special characters in branch names

## Edge Cases to Consider
- Branch names with slashes (already handled by replacement with dashes)
- Subfolder paths with special characters
- Hostname length limits for Docker containers
- Backward compatibility considerations