# Implementation Plan: Detect Changed Extensions

## Overview
Store extension configuration metadata with the container and verify it matches before auto-attaching.

## Implementation Steps

### 1. Store Extension Configuration
- When creating a container, store the full extension list as an environment variable
- Format: `--env ROCKERC_EXTENSIONS=<comma-separated-list>`
- Use rocker's `--env` flag (rocker doesn't support custom Docker labels)
- Store in `prepare_launch_plan()` when building rocker command

### 2. Retrieve Stored Configuration
- Create function `get_container_extensions(container_name: str) -> list[str] | None`
- Use `docker inspect` to read container environment variables
- Parse for `ROCKERC_EXTENSIONS` variable
- Return None if container doesn't exist or env var is missing

### 3. Compare Configurations
- Create function `extensions_changed(current: list[str], stored: list[str]) -> bool`
- Compare sorted extension lists for equality
- Account for edge cases (None, empty lists)

### 4. Update Launch Logic
- In `prepare_launch_plan()`:
  - If container exists and not force:
    - Get stored extensions from container
    - Compare with current configuration
    - If changed: log warning and stop/remove container to require rebuild
  - Continue with existing force/rebuild logic

### 5. Testing
- Test extension list changes trigger rebuild requirement
- Test identical extensions allow reuse
- Test missing env var (old containers) gracefully handled
- Test empty extension lists
- Test extension reordering (should not trigger rebuild)

## Files Modified
- `rockerc/core.py`: Added env injection, comparison functions, updated `prepare_launch_plan()`
- `test/test_extension_detection.py`: New test file for extension change detection
- `test/test_launch_plan.py`: Updated to mock get_container_extensions()
- `test/test_vscode_launcher.py`: Updated assertions for env var approach

## Edge Cases
- Old containers without env var: treat as changed (safe default)
- Extension order changes: normalize by sorting before comparison
- Blacklisted extensions: compare final resolved list, not raw config

## Implementation Notes
- Initially tried Docker labels but rocker doesn't support passing `--label` arguments
- Switched to environment variables which rocker supports via `--env` flag
- Environment variables are persistent in container config and retrievable via docker inspect
