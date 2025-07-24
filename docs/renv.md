# renv - Repository Environment Manager 

## Overview

`renv` is a tool that makes it seamless to work in a variety of repositories at the same time using git worktrees and rocker containers. It automates the process of cloning repositories, managing worktrees for different branches, and launching rocker containers for development.

## Installation

The `renv` command is available as part of the `rockerc` package. When you install `rockerc`, the `renv` command will be available on your PATH.

```bash
pipx install rockerc
```

## Usage

### Basic Syntax

```bash
renv [owner/repo@branch]
```

- `owner/repo`: GitHub repository specification (e.g., `blooop/bencher`, `osrf/rocker`)
- `@branch`: Optional branch name (defaults to `main` if omitted)

### Examples

```bash
# Clone blooop/bencher and switch to main branch
renv blooop/bencher@main

# Clone blooop/bencher and switch to main branch (branch defaults to main)
renv blooop/bencher

# Switch to a feature branch (creates worktree if needed)
renv blooop/bencher@feature/over_time_limited

# Clone and work with a different repository
renv osrf/rocker

# Setup worktree but don't run rockerc (for debugging)
renv blooop/bencher@main --no-container
```

## How It Works

1. **Repository Management**: `renv` clones repositories as bare repos to `~/renv/owner/repo`
2. **Worktree Creation**: For each branch, it creates a separate worktree at `~/renv/owner/repo/worktree-{branch}`
3. **Container Launch**: It runs `rockerc` in the worktree directory to build and enter a rocker container
4. **Branch Switching**: You can easily switch between different branches, each in their own isolated worktree

## Directory Structure

```
~/renv/
├── blooop/
│   └── bencher/                    # Bare repository
│       ├── HEAD
│       ├── config
│       ├── refs/
│       ├── objects/
│       ├── worktree-main/          # Main branch worktree
│       │   ├── rockerc.yaml
│       │   ├── src/
│       │   └── ...
│       └── worktree-feature-xyz/   # Feature branch worktree
│           ├── rockerc.yaml
│           ├── src/
│           └── ...
└── osrf/
    └── rocker/                     # Another repository
        ├── HEAD
        ├── config
        └── worktree-main/
```

## Workflow Examples

### Working on Multiple Branches

```bash
# Start working on main branch
renv blooop/bencher@main

# Switch to feature branch (in a new terminal)
renv blooop/bencher@feature/new-feature

# Switch back to main (preserves both worktrees)
renv blooop/bencher@main
```

### Working on Multiple Repositories

```bash
# Work on one project
renv blooop/bencher@main

# Work on another project (in a new terminal)
renv osrf/rocker@main

# Both environments remain active and isolated
```

## Options

- `--no-container`: Set up the worktree but don't run rockerc (useful for debugging or manual container management)

## Requirements

- Git (for repository and worktree management)
- rockerc (for container management)
- rocker (Docker container tool)

## Branch Name Handling

Branch names containing forward slashes (e.g., `feature/new-feature`) are automatically converted to safe directory names (e.g., `worktree-feature-new-feature`) for the worktree directories.

## Future Enhancements

- **Autocomplete**: Integration with prompt-toolkit for autocompletion of repository names and branch names
- **Repository Discovery**: Automatic discovery of available repositories and branches
- **Cleanup Commands**: Tools to manage and clean up old worktrees

## Troubleshooting

### Repository Already Exists Error
If you get an error about a repository already existing, it means the bare repository has already been cloned. The tool should automatically detect this and fetch the latest changes instead.

### Worktree Creation Fails
If worktree creation fails, it might be because:
1. The branch doesn't exist remotely
2. A worktree for that branch already exists
3. Git permissions issues

Use `git worktree list` in the repository directory to see existing worktrees.

### Container Build Issues
If rockerc fails to build or run the container, check:
1. The `rockerc.yaml` file exists in the worktree
2. Docker is running and accessible
3. rocker is properly installed
