# Implementation Plan

## Changes Required

1. **renv.py:759-774** - Replace custom VSCode handling with unified flow:
   - Instead of `run_rocker_command()` + `launch_vscode()` + `interactive_shell()`
   - Use `core.py:prepare_launch_plan()` to build launch plan with `vscode=True`
   - Use `core.py:execute_plan()` to execute the unified flow
   - This matches how `rockervsc` works via `rockerc.py`

## Testing
- Verify `renvvsc owner/repo@branch` launches container, VSCode, and attaches terminal cleanly
- Ensure terminal formatting is correct and keypresses work properly
