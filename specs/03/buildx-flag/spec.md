# Buildx Flag

Enable Docker Buildx by default via environment variable.

## Scope
- Set `DOCKER_BUILDKIT=1` environment variable by default
- Enables buildx functionality for extensions that use docker commands
- Add `--buildx` CLI flag (enabled by default)