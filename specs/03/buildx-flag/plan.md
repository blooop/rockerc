# Implementation Plan for Buildx Flag

## Changes Required

### 1. Update `_parse_extra_flags()` in `rockerc/rockerc.py`
- Parse `--buildx` flag from command line arguments
- Default buildx to True (enabled by default)
- Return buildx boolean in tuple

### 2. Update `build_docker()` in `rockerc/rockerc.py`
- Change `buildx: bool = False` parameter to `buildx: bool = True`
- Set `DOCKER_BUILDKIT=1` environment variable when buildx=True
- Use same `docker build` command (env var enables buildx)

### 3. Thread `buildx` flag through `run_rockerc()`
- Extract buildx from `_parse_extra_flags()`
- Pass to `build_docker()` when building from dockerfile

## Testing
- Run `pixi run ci` to ensure all tests pass