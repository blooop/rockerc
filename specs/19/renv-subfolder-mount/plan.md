# Plan

1. Review current sparse checkout and container mount logic in `rockerc/renv.py`, `rockerc/core.py`, and helpers to locate where the workspace path is defined.
2. Adjust filesystem preparation so the branch copy exposes only the requested subfolder (likely via bind mounts or working tree path) and ensure `.git` stays reachable.
3. Update container configuration to mount the pruned workspace path, adding regression tests in `test/test_renv.py` or workflow scripts to cover the subfolder isolation case.
4. Validate locally with the relevant workflow script or targeted unit tests, then run `pixi run ci` and iterate until clean.
