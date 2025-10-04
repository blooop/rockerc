# Implementation Plan

## Overview
Prevent internal configuration markers (like `_renv_target_dir`) from being passed to rocker as command-line arguments.

## Steps

1. **Modify `run_rocker_command` function**
   - Add filtering logic to skip keys starting with underscore when building rocker command arguments
   - This prevents internal markers from being passed to rocker

2. **Test the fix**
   - Run existing tests to ensure no regressions
   - Verify container corruption handling works correctly

3. **Run CI**
   - Execute `pixi run ci`
   - Fix any failures
   - Iterate until passing

## Technical Notes
- Keys starting with underscore are reserved for internal use within renv
- The `_renv_target_dir` is popped from config in the normal flow (line 799) but not in the corruption handling path
- By filtering underscored keys in `run_rocker_command`, we make it robust against future additions of internal markers
