# Plan: Submodule Helper Refactor & Test Improvements

1. **Refactor subprocess git calls**
   - Identify all repeated git subprocess.run calls.
   - Create a shared helper utility for git commands.
   - Update all usages to use the helper.

2. **Add logging/error handling for submodule update**
   - Enhance submodule update logic to log errors and raise on failure.
   - Ensure error messages are clear and actionable.

3. **Improve tests**
   - Add a test for nested submodules (multi-level, --recursive).
   - Add a test for repos without submodules.
   - Refactor existing tests to avoid loops/conditionals (use parametrization or helpers).

4. **Validate and iterate**
   - Run `pixi run ci` to ensure all tests and linting pass.
   - Fix any issues until CI is green.

5. **Commit changes**
   - Commit only if CI passes.
