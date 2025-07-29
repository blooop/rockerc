# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`rockerc` is a wrapper around [rocker](https://github.com/osrf/rocker) that reads YAML configuration files to simplify Docker container management. The project consists of two main components:

1. **rockerc** - Core rocker wrapper that reads `rockerc.yaml` files
2. **renv** - Repository Environment Manager that uses git worktrees and containers for multi-repo development

## Development Commands

This project uses [pixi](https://pixi.sh) for dependency management and task running:

### Essential Commands
- `pixi run test` - Run pytest test suite
- `pixi run lint` - Run both ruff and pylint linting
- `pixi run format` - Auto-format code with ruff
- `pixi run ci` - Run full CI pipeline (format, lint, test, coverage)
- `pixi run coverage` - Generate test coverage report

### Individual Tools
- `pixi run ruff-lint` - Run ruff linter with auto-fix
- `pixi run pylint` - Run pylint on all Python files
- `pixi run coverage-report` - Display coverage report in terminal

### Python Environment
- Multiple Python versions supported (3.9-3.13) via pixi environments
- Use `pixi run -e py311 test` to test with specific Python version

## Architecture

### rockerc Core (`rockerc/rockerc.py`)
- **`collect_arguments()`** - Searches for and merges `rockerc.yaml` files
- **`yaml_dict_to_args()`** - Converts YAML config to rocker command arguments
- **`run_rockerc()`** - Main entry point that orchestrates the rocker execution
- **Container management** - Handles existing container attachment and conflict resolution
- **Dockerfile building** - Supports building custom images from Dockerfiles

### renv (`rockerc/renv.py`)
- **Git worktree management** - Creates isolated working directories for different branches
- **Repository cloning** - Handles bare repository cloning and fetching
- **Container lifecycle** - Manages named containers per repo@branch combination
- **Fuzzy selection** - Interactive repo/branch selection with fzf integration
- **Bash completion** - Tab completion for repository specifications

### Key Data Flow
1. `renv` parses repo specification (owner/repo@branch#subfolder)
2. Sets up git worktree and mounts both bare repo and worktree in container
3. Calls `rockerc` with proper volume mounts and working directory
4. `rockerc` reads local `rockerc.yaml` + global defaults, merges config
5. Builds rocker command and executes (or attaches to existing container)

## Configuration Files

- **`rockerc.yaml`** - Local project configuration (image, extensions, etc.)
- **`rockerc.defaults.yaml`** - Global defaults loaded by renv
- **`rockerc.defaults.template.yaml`** - Template for creating defaults

## Testing

Tests are located in `test/` directory:
- Unit tests for core functionality
- Integration tests for workflow scenarios
- Test workflows in `test/workflows/` directory

## Important Implementation Details

- Uses bare git repositories + worktrees to enable simultaneous work on multiple branches
- Container names are generated as `{repo}-{branch}` format
- Supports container reuse - attaches to existing containers instead of recreating
- Environment variables `GIT_DIR` and `GIT_WORK_TREE` are set for proper git operations in containers
- Special handling for `disable_args` to remove unwanted rocker extensions
- Automatic SSH key setup for GitHub cloning