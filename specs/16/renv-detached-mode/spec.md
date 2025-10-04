# Make renv Use Detached Mode Like rockerc

## Problem
Currently, `renv` in terminal mode runs containers in foreground mode, which means:
- Exiting the shell removes the container
- No container reuse across multiple `renv` invocations
- Different behavior from `rockerc` which uses detached mode

## Expected Behavior
`renv` should match `rockerc` behavior:
- Launch container in detached mode, then attach interactively via `docker exec`
- Exiting the interactive session leaves the container running
- Subsequent `renv` calls with same repo/branch reuse the existing container
- When running commands (e.g., `renv blooop/test_renv -- pwd`):
  - Create container detached (if not exists)
  - Attach and run the command via `docker exec`
  - Exit but leave container running
- Container persistence allows state to be maintained (e.g., files created in one session are visible in the next)

## Implementation
- Update `manage_container()` terminal mode to use detached workflow
- Leverage existing `core.py` functions: `prepare_launch_plan()`, `execute_plan()`, `wait_for_container()`
- For command execution, use `docker exec` instead of passing command to rocker
- Ensure volume mounts and settings are preserved for container reuse
