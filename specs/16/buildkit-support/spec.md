# Buildkit Support

## Problem
Rocker currently doesn't use Docker's BuildKit by default, which limits performance and features for container builds. BuildKit provides improved caching, parallelization, and advanced dockerfile features.

## Solution
Always set the `DOCKER_BUILDKIT=1` environment variable when calling rocker or docker build commands from rockerc.

## Requirements
- All subprocess calls to rocker should have `DOCKER_BUILDKIT=1` in the environment
- Direct docker build calls should also have `DOCKER_BUILDKIT=1` in the environment
- This should be transparent to users - no configuration changes required
- Maintain backward compatibility

## Implementation Points
- `launch_rocker()` function in `rockerc/core.py`
- `build_docker()` function in `rockerc/rockerc.py`  
- `run_rocker_command()` function in `rockerc/renv.py`
- `manage_container()` subprocess.run call in `rockerc/renv.py`