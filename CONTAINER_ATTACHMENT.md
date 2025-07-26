# Container Attachment Feature

The `rockerc` tool now automatically handles cases where a Docker container with the same name already exists.

## How it works

When you run `renv` and it tries to create a container with a name that already exists, instead of failing with a "container name already in use" error, `rockerc` will:

1. **Check if container exists**: First check if a container with the target name already exists
2. **Attach to existing container**: If it exists, attach to it directly instead of trying to create a new one
3. **Start if stopped**: If the container exists but is stopped, start it first then attach
4. **Fallback on failure**: If attachment fails, provide helpful error messages with commands to remove the conflicting container

## Benefits

- **Seamless workflow**: No more manual container cleanup when switching between branches
- **Faster startup**: Attaching to existing containers is faster than creating new ones
- **State preservation**: Your existing container state is preserved between sessions

## Error handling

If attachment fails, you'll see helpful error messages like:

```
You may need to remove the existing container:
  docker rm container-name
Or remove it forcefully if it's running:
  docker rm -f container-name
```

## Technical details

The feature works by:

1. Extracting the container name from rocker command arguments (looks for `--name` flag)
2. Running `docker ps -a` to check if container exists
3. Running `docker ps` to check if container is running
4. Using `docker start` to start stopped containers
5. Using `docker exec -it container-name /bin/bash` to attach to running containers

## Automatic detection

The system automatically detects container name conflicts by looking for these error patterns:
- `"already in use"` in error output
- `"Conflict"` in error output

## Example workflow

```bash
# First time - creates new container
renv blooop/repo@branch1

# Later - attaches to existing container 
renv blooop/repo@branch1  # No conflict, just attaches!

# Different branch - creates new container
renv blooop/repo@branch2

# Back to first branch - attaches again
renv blooop/repo@branch1  # Attaches to existing container
```

This makes the development workflow much smoother when working with multiple branches and containers.
