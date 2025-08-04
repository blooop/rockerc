# Example Repository with Custom Extensions

This is an example repository that demonstrates the new modular extension system in worktree_docker.

## Custom Extensions

This repository includes a custom extension in `.worktree_docker/extensions/custom-tool/` that:

1. Installs a simple command-line tool called `custom-tool`
2. Sets environment variables for the tool configuration
3. Is automatically discovered and loaded when using worktree_docker

## File Structure

```
.worktree_docker/
└── extensions/
    └── custom-tool/
        ├── Dockerfile           # Docker build instructions
        └── docker-compose.yml   # Environment and volume configuration
```

## Features Demonstrated

- **Auto-discovery**: The custom extension is automatically detected
- **Auto-detection**: The pyproject.toml file triggers the uv extension
- **Modular design**: Each extension is self-contained in its own directory
- **Compose integration**: Extensions can define their own environment variables

## Usage

```bash
# From this directory, worktree_docker will automatically discover and load:
# 1. Built-in extensions (base, user)
# 2. Auto-detected extensions (uv from pyproject.toml)  
# 3. Custom local extensions (custom-tool from .worktree_docker/extensions/)

worktree_docker your-repo@main
```