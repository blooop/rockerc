# Changelog

## rockerc

## [0.19.0] - 2026-08-07
### Removed
- `aid`. It is superseded by devlaunch's `aid` (devlaunch 0.0.9), and the two
  collided: both packages installed an `aid` entry point, so whichever landed
  later on `PATH` won. This `aid` reached a repo through `renv`/rocker, composing
  and building an image per launch, where devlaunch's `dl` drives devpod and
  reuses the workspace it already has for that branch — the same repo and branch
  gave you two different containers depending on which `aid` you got. devlaunch's
  `aid` has no container machinery of its own: it rewrites its command line into
  a `dl` one, so there is one path to a workspace and nothing to drift.

  Gone with it: `rockerc/aid.py`, the `aid` entry point, its completion script
  and its tests. `rockerc --install` still strips a leftover `aid` completion
  from `~/.bashrc`, so upgrading cleans up after the old command.

  `rockerc`, `renv`, `renvvsc`, `rockervsc` and `dp` are unaffected.

  Note for anyone who used the flags: devlaunch's `aid` defaults to `--claude`
  rather than `--gemini`, and has no equivalent yet for the gemini-only
  `-y/--yolo` and `-f/--flash`.

## [0.13.0] - 2025-09-29
### Added
- Unified always-detached execution model: rocker container is always started (or reused) in detached mode and shell access provided via `docker exec`.
- `--vsc` flag for `rockerc` to launch & attach VS Code to the running container.
- `rockervsc` now a thin alias for `rockerc --vsc`.
- Force behavior (`--force` / `-f`) renames existing container (timestamp) before launching a new one.
- Environment variables `ROCKERC_WAIT_TIMEOUT` and `ROCKERC_WAIT_INTERVAL` to tune container availability polling.
- Generated artifacts (`Dockerfile.rocker`, `run_dockerfile.sh`) when `create-dockerfile` is requested.
- Additional tests for launch plan edge cases: container reuse, force path, required flag injection.

### Changed
- Consolidated VS Code attach logic and container lifecycle handling into `core.py` helpers.
- README updated with unified flow documentation and troubleshooting notes.

### Removed
- Legacy foreground rocker execution path (now always detached).
- Temporary `PlanOptions` dataclass (reverted to direct function signature with pylint suppression).

### Fixed
- Prior NameError risk around `derive_container_name` import ordering.
- Intermittent TTY/key input issues by eliminating shared stdin with rocker process.

## [0.12.0]
Historical releases prior to 0.13.0 not fully enumerated here.

## [0.2.0]
