# renv-match-rockerc

## Goal
Make the `renv` command behave the same as `rockerc`:
- When running `renv`, it should build and run the image in detached mode, then attach interactively to the running container.
- Exiting the interactive session should not remove the container (matching `rockerc` behavior).

## Acceptance Criteria
- `renv` launches the container in detached mode, then attaches interactively.
- Exiting the shell leaves the container running.
- Behavior matches `rockerc` for build/run/attach lifecycle.
- No regression in existing `renv` or `rockerc` functionality.
