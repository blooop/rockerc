# Fix renvvsc to use unified flow from core.py

## Problem
`renvvsc` uses custom container management causing terminal formatting issues and missed keypresses, unlike `rockervsc` which works cleanly.

## Expected Behavior
Match `rockervsc` flow using `core.py`'s unified flow:
1. Build/start container (detached)
2. Launch VSCode
3. Attach interactive shell to container

## Current Behavior
`renv.py` uses custom `run_rocker_command()` and manual `interactive_shell()` call instead of unified flow.

## Solution
Use `core.py:prepare_launch_plan()` and `core.py:execute_plan()` for VSCode mode to match `rockervsc` behavior.
