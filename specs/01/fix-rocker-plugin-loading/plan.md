
# Plan

1. Refactor manage_container and related logic in `rockerc/renv.py`:
	- Move subfolder mount handling and cwd restoration into helper functions.
	- Introduce a `cwd` context manager for directory changes.
	- Extract sparse-checkout logic into a helper.
	- Refactor repeated `subprocess.run` git invocations into a shared utility.
2. Update repo name parsing for legacy layouts to use `rsplit("-", 1)` for correct handling of multiple dashes.
3. Add checks/warnings to legacy workspace migration to prevent overwriting existing data.
4. Improve error handling in `_restore_cwd` to log and raise if restoration fails.
5. Refactor volume binding logic in `rockerc/core.py` to use structured parsing for deduplication.
6. Refactor `build_rocker_config` to reduce complexity and improve readability.
7. Add a test for branch setup when upstream exists (`_has_upstream=True`).
8. Add a positive test for sparse checkout path verification when the subfolder exists.
9. Add a test for duplicate volume entries in launch plan.
10. Refactor tests in `test/workflows/test_workflows.py` to avoid loops, using parametrization or helpers.
11. Run `pixi run ci` and iterate until all checks pass.
12. Commit changes when ci passes.
