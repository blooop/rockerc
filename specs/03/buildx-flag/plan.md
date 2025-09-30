# Implementation Plan for Buildx Flag

## Changes Required

### 1. Update `_parse_extra_flags()` in `rockerc/rockerc.py`
- Add `buildx` boolean to return tuple
- Parse `--buildx` flag from command line arguments
- Return updated tuple with buildx flag

### 2. Update `build_docker()` in `rockerc/rockerc.py`
- Add `buildx: bool = False` parameter
- Conditionally use `docker buildx build` vs `docker build`
- Keep all other behavior identical

### 3. Thread `buildx` flag through `run_rockerc()`
- Extract buildx from `_parse_extra_flags()`
- Pass to `build_docker()` when building from dockerfile

## Testing
- Run `pixi run ci` to ensure all tests pass
- Verify backward compatibility (without flag)