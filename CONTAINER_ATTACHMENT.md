# Container Attachment and Git Integration Features

The `rockerc` tool now automatically handles cases where a Docker container with the same name already exists, and provides seamless git integration for worktrees and subfolders.

## Container Attachment

When you run `renv` and it tries to create a container with a name that already exists, instead of failing with a "container name already in use" error, `rockerc` will:

1. **Check if container exists**: First check if a container with the target name already exists
2. **Attach to existing container**: If it exists, attach to it directly instead of trying to create a new one
3. **Start if stopped**: If the container exists but is stopped, start it first then attach
4. **Set working directory**: Automatically set the working directory to `/workspaces` when attaching
5. **Fallback on failure**: If attachment fails, provide helpful error messages with commands to remove the conflicting container

## Git Integration

The system now properly handles git repositories in containers:

- **Correct working directory**: When attaching to containers, the shell starts in `/workspaces` where your git repository is mounted
- **Worktree support**: Full support for git worktrees created by renv
- **Subfolder support**: You can work in specific subfolders of repositories using the `#subfolder` syntax

## Subfolder Syntax

You can now specify a subfolder within a repository:

```bash
# Work in the main branch, scripts folder
renv blooop/rockervsc@main#scripts

# Work in a feature branch, docs folder  
renv blooop/rockervsc@feature-branch#docs

# Work in subdirectories with paths
renv blooop/rockervsc@main#src/python
```

### Subfolder Benefits

- **Container isolation**: Each subfolder gets its own container to avoid conflicts
- **Git functionality**: Full git commands work even when in a subfolder
- **Directory focus**: Start directly in the folder you want to work in

## Benefits

- **Seamless workflow**: No more manual container cleanup when switching between branches
- **Faster startup**: Attaching to existing containers is faster than creating new ones
- **State preservation**: Your existing container state is preserved between sessions
- **Git integration**: Git commands work naturally from within containers
- **Flexible workflows**: Work in full repositories or focus on specific subfolders

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
5. Using `docker exec -it -w /workspaces container-name /bin/bash` to attach with correct working directory
6. Handling subfolder navigation by changing directory before running rockerc
7. Including subfolder names in container names to avoid conflicts

## Automatic detection

The system automatically detects container name conflicts by looking for these error patterns:
- `"already in use"` in error output
- `"Conflict"` in error output

## Example workflows

### Basic workflow
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

### Subfolder workflow
```bash
# Work on scripts in main branch
renv blooop/repo@main#scripts

# Work on documentation in same branch (different container)
renv blooop/repo@main#docs

# Work on scripts in feature branch
renv blooop/repo@feature#scripts
```

### Git usage in containers
```bash
# Inside container - all git commands work normally
git status
git add .
git commit -m "Update from container"
git push origin main

# Even in subfolders, git commands work on the full repository
cd /workspaces/scripts
git status  # Shows status of entire repository
git log     # Shows full repository history
```

This makes the development workflow much smoother when working with multiple branches, containers, and repository subfolders.
