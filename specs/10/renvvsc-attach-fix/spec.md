# Fix renvvsc terminal formatting and keypress issues

## Problem
`renvvsc` has terminal formatting issues and misses keypresses, unlike `rockervsc` which works cleanly.

## Root Cause
`renv` changes working directory for container launch (needed for `cwd` extension) but keeps it changed during VSCode attach and interactive shell. This differs from `rockervsc` which never changes cwd and exits immediately via `sys.exit()`.

## Expected Behavior
Match `rockervsc` clean terminal handling:
1. Build/start container (detached) - with cwd change
2. Restore original cwd before attach operations
3. Launch VSCode - with original cwd
4. Attach interactive shell - with original cwd

## Solution
Restore working directory immediately after container launch, before VSCode and shell attach operations.
