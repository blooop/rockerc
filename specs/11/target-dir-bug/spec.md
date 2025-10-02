# Fix container breakout detection errors

## Problem 1: _renv_target_dir passed to rocker
When container corruption is detected, `renv` passes `--_renv_target_dir` to rocker, which doesn't recognize this argument, causing the command to fail with "unrecognized arguments: --_renv_target_dir".

## Problem 2: docker exec fails with breakout detection
When attaching to an existing container, `docker exec` fails with "current working directory is outside of container mount namespace root -- possible container breakout detected" because the Python process is in a directory not mounted in the container.

## Root Cause
1. `_renv_target_dir` is an internal configuration marker that gets passed to rocker
2. After spec 10's fix to restore `original_cwd` before attach operations, the Python process is in a directory (like `/home/user`) that's not mounted in the container, triggering Docker's security check on `docker exec`

## Solution
1. Filter out keys starting with underscore in `run_rocker_command` when building rocker arguments
2. Before calling `docker exec` operations (`interactive_shell`, `attach_to_container`), change to `branch_dir` which is always mounted in the container
