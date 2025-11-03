# Implementation Plan: --nocache Flag Support

## Current State
- CLI parsing: ✓ Works (`renv.py:1419-1430`)
- Function parameters: ✓ Declared (`renv.py:674, 1058`)
- Rocker injection: ✗ Missing (never added to rocker command)

## Implementation Steps

### 1. Update `renv.py` to pass nocache to prepare_launch_plan
**File**: `rockerc/renv.py`
**Line**: 1277

Change:
```python
plan = core.prepare_launch_plan(
    args_dict=config,
    force=force,
    ...
)
```

To:
```python
plan = core.prepare_launch_plan(
    args_dict=config,
    force=force,
    nocache=nocache,
    ...
)
```

### 2. Update `prepare_launch_plan()` signature in core.py
**File**: `rockerc/core.py`

Add `nocache` parameter to function signature and pass it to `build_rocker_arg_injections()`.

### 3. Update `build_rocker_arg_injections()` in core.py
**File**: `rockerc/core.py`

Add logic to inject `--nocache` flag when `nocache=True`:
```python
if nocache:
    extra_args["nocache"] = True
```

### 4. Test Changes
Run `pixi run ci` to verify:
- Unit tests pass
- Integration tests pass
- Linting passes

### 5. Manual Verification
Test command: `renv blooop/test_renv --nocache`
Expected: rocker command includes `--nocache` flag

## Files to Modify
1. `rockerc/renv.py` (line ~1277)
2. `rockerc/core.py` (`prepare_launch_plan()` and `build_rocker_arg_injections()`)

## Testing Strategy
- Existing tests should pass
- Add test case to verify nocache flag propagation
- Manual test with actual renv command
