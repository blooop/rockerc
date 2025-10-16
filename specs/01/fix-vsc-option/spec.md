# Fix --vsc Option in renv

## Problem
The --vsc option in renv has broken. Previously, running `renv --vsc` or `renvvsc` would:
- Launch a detached container
- Attach VSCode
- Attach a terminal

Currently, regular renv works but passing --vsc causes the container to crash.

## Root Cause
The container crashes in VSCode mode because it lacks a keep-alive process.

**Container lifecycle issue:**
- **Regular renv**: Adds `["tail", "-f", "/dev/null"]` to keep container alive
- **VSCode renv**: No keep-alive command → container exits immediately after launch
- **rockervsc**: Works because `interactive_shell()` immediately attaches and keeps container alive

**Timeline of failure:**
1. Container launches successfully with rocker
2. Container immediately exits (no process to keep it running)
3. VSCode attachment fails (container is dead)
4. Terminal attachment fails (container is dead)

## Solution
Add the missing keep-alive command to VSCode mode so containers don't exit immediately after launch.

## Changes Made
1. **Add keep-alive command in VSCode mode** - `plan.rocker_cmd.extend(["tail", "-f", "/dev/null"])`
2. **Match regular renv behavior** - both modes now use the same container lifecycle
3. **Improve shell handling** - use `subprocess.call()` and proper shell detection for consistency

This ensures the container stays running until the interactive shell attaches, preventing the crash.

## Expected Outcome
- --vsc option works as before
- Container launches successfully with VSCode and terminal attached
