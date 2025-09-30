# Buildx Flag

Add a `buildx` flag to enable Docker Buildx for building images.

## Scope
- Add `--buildx` CLI flag
- Modify `build_docker()` to use `docker buildx build` when flag is set
- Default behavior remains `docker build` (no flag)