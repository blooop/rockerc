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
- Remove `cwd` extension, use explicit `/workspaces/<container_name>` mount and `docker exec -w`
- Use `prepare_launch_plan()` from core.py for unified container lifecycle
- Add `tail -f /dev/null` to keep detached containers running
- Extension change detection automatically rebuilds containers when configuration changes
- Force rebuild when transitioning from old cwd-based containers
