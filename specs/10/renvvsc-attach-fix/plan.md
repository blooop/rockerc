# Implementation Plan

## Changes Required

1. **renv.py:763-781** - Replace custom VSCode handling with core.py flow components:
   - Import `wait_for_container`, `launch_vscode`, `container_hex_name`, `interactive_shell` from core
   - After launching detached container, call `wait_for_container()` to ensure readiness
   - Call `launch_vscode()` with proper container hex name
   - Call `interactive_shell()` to attach terminal
   - This matches the flow in `core.py:execute_plan()` used by `rockervsc`

## Implementation Notes
- Cannot use `prepare_launch_plan()` directly due to config format mismatch
- `renv` uses custom config building incompatible with `prepare_launch_plan()`
- Instead, use individual flow components to achieve same behavior

## Testing
- Verify `renvvsc owner/repo@branch` launches container, VSCode, and attaches terminal cleanly
- Ensure terminal formatting is correct and keypresses work properly
