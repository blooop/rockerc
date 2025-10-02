# Implementation Plan

## Root Cause Analysis
`renv` has architectural differences from `rockerc`:
1. Changes working directory to allow `cwd` extension to detect correct path during launch
2. Keeps cwd changed during attach operations (VSCode + shell)
3. Uses try/finally for cwd restoration

`rockerc` in contrast:
1. Never changes working directory
2. Exits immediately via `sys.exit()` after `execute_plan()`

The cwd change during interactive shell attach causes TTY handling issues.

## Solution
Restore working directory **between** container launch and attach operations:
1. Change cwd before launching container (needed for `cwd` extension)
2. **Restore cwd immediately after container launch**
3. Launch VSCode with original cwd
4. Attach shell with original cwd

## Changes Required

1. **renv.py:771-773** - Add `os.chdir(original_cwd)` after container launch, before attach operations

## Testing
- Verify `renvvsc owner/repo@branch` launches container, VSCode, and attaches terminal cleanly
- Ensure terminal formatting is correct and keypresses work properly
- Verify `cwd` extension still works correctly (container launches with correct working directory)
