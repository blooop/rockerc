# Implementation Plan: Buildkit Support

## Overview
Enable Docker BuildKit for all rocker and docker build calls to improve build performance and enable advanced features.

## Steps

1. **Update launch_rocker function in core.py**
   - Modify subprocess.run call to include DOCKER_BUILDKIT=1 in environment
   - Use existing environment and add buildkit flag

2. **Update build_docker function in rockerc.py**
   - Modify subprocess.call to include DOCKER_BUILDKIT=1 in environment
   - Ensure buildkit is used for local dockerfile builds

3. **Update run_rocker_command function in renv.py**
   - Modify subprocess.run and subprocess.Popen calls to include DOCKER_BUILDKIT=1
   - Handle both detached and non-detached modes

4. **Update manage_container function in renv.py**
   - Modify the subprocess.run call around line 891 to include DOCKER_BUILDKIT=1
   - This handles container rebuilding scenarios

5. **Test the implementation**
   - Run `pixi run ci` to ensure no regressions
   - Verify buildkit is actually being used (can be confirmed by improved build performance and advanced features)

6. **Commit changes**
   - Commit the spec and implementation once all tests pass

## Technical Notes
- Use `env = {**os.environ, 'DOCKER_BUILDKIT': '1'}` pattern to preserve existing environment
- BuildKit is backward compatible, so this shouldn't break existing functionality
- BuildKit has been the default in newer Docker versions, but explicitly setting it ensures consistency