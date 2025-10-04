
# Plan: Container Breakout Test

1. Update the shell script `test_workflow_7_container_breakout.sh` to:
   - Run `renv blooop/test_renv pwd`.
   - Delete `~/renv`.
   - Run `renv blooop/test_renv pwd` again.
   - Ensure all steps are serial (no concurrency).
2. Add a Python test (e.g., `test_container_breakout.py`) that:
   - Runs the updated shell script.
   - Captures the output.
   - Asserts that the output contains a message about container breakout and that a rebuild occurs.
3. Commit only the contents of `specs/14/container-breakout-test/`.
