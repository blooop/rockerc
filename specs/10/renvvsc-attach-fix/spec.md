# Fix renvvsc to attach to container after launching VSCode

## Problem
`renvvsc` currently launches container and VSCode but returns without attaching to the container terminal.

## Expected Behavior
Match `rockervsc` flow:
1. Build/start container
2. Launch VSCode
3. Attach interactive shell to container

## Current Behavior
`renv.py:760-772` returns after launching VSCode (line 772 `return 0`)

## Solution
After `launch_vscode()`, call `interactive_shell()` instead of returning.
