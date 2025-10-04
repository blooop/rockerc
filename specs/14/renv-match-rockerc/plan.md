# Plan: Make `renv` match `rockerc` container lifecycle

## Steps

1. **Analyze current `renv` and `rockerc` behavior**
   - Review how `rockerc` builds, runs (detached), and attaches to containers.
   - Review how `renv` currently runs containers (likely not detached).

2. **Update `renv` to run containers detached**
   - Modify `renv` to start containers in detached mode (e.g., with `-d` flag).
   - Ensure container is not removed on exit.

3. **Implement attach logic in `renv`**
   - After starting the container, attach interactively to it (like `rockerc`).

4. **Test and verify behavior**
   - Run `renv` and confirm it matches `rockerc` lifecycle.
   - Ensure exiting the shell leaves the container running.
   - Check for regressions in both commands.

5. **Update spec if clarifications arise**
   - Document any edge cases or clarifications in `spec.md`.

6. **Commit changes in `specs/14/renv-match-rockerc/`**

7. **Implement code changes**
   - Update `renv.py` (and related files if needed).
   - Run `pixi run ci` and iterate until passing.
   - Commit only if CI passes.
