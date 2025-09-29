# Changelog

## rockerc

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

## [0.0.0]
