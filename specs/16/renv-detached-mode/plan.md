# Implementation Plan

## Changes to renv.py

### 1. Update `manage_container()` terminal mode (lines 906-956)
Replace the current terminal mode flow with detached workflow:

**Current flow:**
- Checks if container running
- If exists: attach directly
- If not: run rocker in foreground (NOT detached)

**New flow:**
- Use `prepare_launch_plan()` from core.py (same as rockerc)
- If container doesn't exist or forced: launch detached with rocker
- Wait for container with `wait_for_container()`
- For commands: use `docker exec` to run command in container
- For interactive: use `interactive_shell()` from core.py

### 2. Handle command execution
When `command` is provided:
- Don't pass command to rocker (rocker launches bare container)
- After container is running, use `docker exec` to run the command
- Ensure proper exit code propagation

### 3. Update tests
Tests that run commands directly with renv need to account for detached workflow:
- Container persists between test runs
- May need cleanup/teardown for container removal
- Commands run via `docker exec` not rocker

## Testing Steps
1. Run `pixi run ci` to ensure tests pass
2. Manual testing:
   - `renv blooop/test_renv` - should launch detached and attach
   - Exit shell - container should remain running
   - `renv blooop/test_renv` again - should reuse container
   - `renv blooop/test_renv -- touch file.txt` - should create file in container
   - `renv blooop/test_renv -- ls` - should show file.txt
