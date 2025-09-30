# Implementation Plan: Detect Changed Extensions

## Overview
Store extension configuration metadata with the container and verify it matches before auto-attaching.

## Implementation Steps

### 1. Store Extension Configuration
- When creating a container, store the full extension list as a Docker label
- Label format: `rockerc.extensions=<comma-separated-list>`
- Store in `prepare_launch_plan()` when building rocker command

### 2. Retrieve Stored Configuration
- Create function `get_container_extensions(container_name: str) -> list[str] | None`
- Use `docker inspect` to read the `rockerc.extensions` label
- Return None if container doesn't exist or label is missing

### 3. Compare Configurations
- Create function `extensions_changed(current: list[str], stored: list[str]) -> bool`
- Compare sorted extension lists for equality
- Account for edge cases (None, empty lists)

### 4. Update Launch Logic
- In `prepare_launch_plan()`:
  - If container exists and not force:
    - Get stored extensions from container
    - Compare with current configuration
    - If changed: log warning and set `created=True` to require rebuild
  - Continue with existing force/rebuild logic

### 5. Testing
- Test extension list changes trigger rebuild requirement
- Test identical extensions allow reuse
- Test missing label (old containers) gracefully handled
- Test empty extension lists
- Test extension reordering (should not trigger rebuild)

## Files to Modify
- `rockerc/core.py`: Add label injection, comparison functions, update `prepare_launch_plan()`
- `test/test_extension_detection.py`: New test file for extension change detection

## Edge Cases
- Old containers without labels: treat as changed (safe default)
- Extension order changes: normalize by sorting before comparison
- Blacklisted extensions: compare final resolved list, not raw config
