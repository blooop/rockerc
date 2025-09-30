# Implementation Plan

## Analysis
Current renv.py has custom container management in `manage_container()`:
- Custom container existence/running checks
- Custom attach logic with fallback
- Custom rocker command building
- Does NOT use core.py's unified flow

## Changes Needed

### 1. Refactor renv.py to use core.py
- Replace custom `run_rocker_command()` with core's approach
- Use `prepare_launch_plan()` and `execute_plan()` from core.py
- Keep renv-specific logic (worktrees, repo management, config merging)
- Remove duplicate container lifecycle management

### 2. Simplify renvsc.py
- Make renvvsc a thin wrapper like rockervsc
- Add `--vsc` flag and delegate to renv's main function
- Remove duplicate container management logic

### 3. Update renv to accept --vsc flag
- Modify run_renv() to accept and handle --vsc flag
- Pass vsc flag through to core.py's prepare_launch_plan()

## Benefits
- Single code path for container management
- Consistent behavior between rockerc and renv
- Easier maintenance (changes in core.py benefit both)
- Less code duplication
