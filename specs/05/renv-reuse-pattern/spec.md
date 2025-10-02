# Renv Reuse Pattern

## Current State
- `rockerc`: Uses `core.py` for container management (detached launch, VS Code attach)
- `rockervsc`: Thin wrapper that adds `--vsc` flag and calls `run_rockerc()`
- `renv`: Has its own container management logic, doesn't use `core.py`
- `renvsc`: Partially implemented, attempts to replicate renv logic for VSCode

## Goal
Make renv follow the same reuse pattern as rockerc:
- renv should use core.py functionality where applicable
- renvvsc should be a thin wrapper like rockervsc that delegates to renv with VSCode flag

## Key Pattern
```
rockerc (uses core.py) ←── rockervsc (adds --vsc flag)
    ↓                              ↓
renv (uses core.py)    ←── renvvsc (adds --vsc flag)
```

Both renv and renvvsc should leverage the unified container launch flow from core.py.
