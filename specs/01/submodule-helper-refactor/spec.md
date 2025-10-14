# Submodule Helper Refactor & Test Improvements

## Summary
- Refactor repeated `subprocess.run` git calls into a shared helper utility for consistency and deduplication.
- Add logging and error handling for submodule update steps to surface failures.
- Add a test for nested (multi-level) submodules to verify `--recursive` behavior.
- Add a test for repos without submodules to ensure graceful handling.
- Refactor tests to avoid loops and conditionals, using parametrization or helpers.

## Acceptance Criteria
- All git subprocess logic uses a shared helper.
- Submodule update errors are logged and surfaced.
- Tests for nested and no-submodule cases exist and pass.
- No loops or conditionals in test bodies (use parametrization/helpers).
- CI passes.
