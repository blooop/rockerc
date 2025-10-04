# Implementation Plan

## Changes Required

### Update `manage_container()` in `rockerc/renv.py`
Remove line 925 that strips the `cwd` extension for terminal mode:
```python
# REMOVE THIS LINE:
config["args"] = [ext for ext in config.get("args", []) if ext != "cwd"]
```

The cwd extension is already added at line 514 for all modes. Terminal mode already uses `docker exec -w` to set the working directory (lines 1008, 1018, 1021), which works fine with the cwd extension.

## Expected Behavior After Fix

### Scenario: renv then renvvsc
```bash
$ renv blooop/rockerc@feature/buildkit
# Creates container with cwd extension
# Uses docker exec -w to set working directory

$ renvvsc blooop/rockerc@feature/buildkit
# Attaches to existing container (no rebuild, extensions match)
# Uses cwd extension WORKDIR
# VSCode opens successfully
```

### Scenario: renv with --force
```bash
$ renv --force blooop/rockerc@feature/buildkit
# Forces rebuild regardless (existing behavior maintained)
```
