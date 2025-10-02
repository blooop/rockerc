# Implementation Plan

## Changes Required

1. **renv.py:760-772** - Modify VSCode mode handling:
   - After `launch_vscode()`, call `interactive_shell()` from core.py
   - Remove the `return 0` that exits early
   - Let the function fall through to interactive shell attachment

## Testing
- Verify `renvvsc owner/repo@branch` launches container, VSCode, and attaches terminal
- Ensure terminal attachment works after VSCode launch
