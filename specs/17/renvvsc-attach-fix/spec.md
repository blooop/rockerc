# Fix renvvsc Extension Change Detection

## Problem
When `renv` creates a container, then `renvvsc` tries to attach to it, the extension change detection triggers an unnecessary rebuild. This happens because:
- `renv` (terminal mode) removes the `cwd` extension (line 925)
- `renvvsc` (VSCode mode) includes the `cwd` extension (added at line 514)
- `prepare_launch_plan()` detects this difference and rebuilds the container

## Solution
Keep the `cwd` extension for both terminal and VSCode modes. The cwd extension sets WORKDIR in the container, which works fine for both modes:
- VSCode mode: Uses the WORKDIR set by cwd extension
- Terminal mode: Can still override with `docker exec -w` when needed (already does this)

## Requirements
- Both `renv` and `renvvsc` should use the same extension list (including `cwd`)
- Remove the code that strips `cwd` for terminal mode
- Maintain backward compatibility
