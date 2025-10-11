# Auto Extension Workspace Path Handling

## Summary
Fix argument parsing in `rockerc` so that the workspace path after `--auto` is passed to the auto extension as its argument, defaults to cwd if not provided, and is not used as a Docker base image. Ensure both `rockerc --auto ~/renv -- ubuntu:24.04` and `rockerc --auto -- ubuntu:24.04` work as intended.

## Acceptance Criteria
- The auto extension receives the correct workspace path argument from rockerc.
- The Dockerfile generated does not use the workspace path as a base image.
- Running with and without a workspace path works identically to rocker.
- If no path is provided, auto defaults to the current working directory.
- The workspace path is not used as a Docker base image.
