# Plan: Auto Extension Workspace Path Handling

1. **Analyze CLI argument parsing for --auto**
   - Identify how workspace path and image are parsed.
   - Ensure nargs="?" behavior for workspace path.

2. **Update argument parsing logic**
   - Pass workspace path after --auto to the auto extension.
   - If no path is provided, default to cwd.
   - Ensure workspace path is not used as Docker base image.

3. **Validate behavior**
   - Test with `rockerc --auto ~/renv -- ubuntu:24.04` (auto scans ~/renv, image is ubuntu:24.04).
   - Test with `rockerc --auto -- ubuntu:24.04` (auto scans cwd, image is ubuntu:24.04).

4. **Update spec.md if clarifications are needed**
   - Keep spec concise and up to date.

5. **Run CI and commit if passing**
   - Ensure all tests and linting pass before final commit.
