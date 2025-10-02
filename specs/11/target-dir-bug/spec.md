# Fix _renv_target_dir being passed to rocker

## Problem
When container corruption is detected, `renv` passes `--_renv_target_dir` to rocker, which doesn't recognize this argument, causing the command to fail with "unrecognized arguments: --_renv_target_dir".

## Root Cause
In `_handle_container_corruption` (renv.py:742-743), the config dict containing `_renv_target_dir` is passed directly to `run_rocker_command` without removing this internal marker first.

`_renv_target_dir` is an internal configuration value used by renv to track the target directory for `os.chdir()` before launching containers. It should never be passed to rocker.

## Solution
Filter out keys starting with underscore in `run_rocker_command` when building rocker arguments, as these are internal markers not meant for rocker.
