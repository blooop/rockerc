# Spec: Pass --nocache Flag from renv to rocker

## Problem
The `--nocache` flag is parsed by renv's CLI but never passed to rocker, so Docker builds always use cache even when the user requests `--nocache`.

## Solution
Inject the `--nocache` flag into the rocker command when the user provides it to renv.

## Changes Required
1. Pass `nocache` parameter to `prepare_launch_plan()` in `renv.py:1277`
2. Handle `nocache` in `build_rocker_arg_injections()` in `core.py`
3. Add `--nocache` to the rocker command when flag is set

## Expected Behavior
```bash
renv blooop/test_renv --nocache
# Should result in: rocker --nocache --user --git --pull --detach --name container -- ubuntu:20.04
```
