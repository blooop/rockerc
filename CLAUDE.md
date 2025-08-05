# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

worktree_docker (CLI: `wtd`) is a development environment launcher that combines Git worktrees with Docker containers and BuildKit caching. It automates repository cloning, branch switching, and container management for isolated multi-repo development environments. The tool automatically builds cached Docker environments using extensions and launches development containers for each repo/branch combination.

## Development Commands

This project uses [Pixi](https://pixi.sh) for package and environment management. All commands are defined in `pyproject.toml` under `[tool.pixi.tasks]`.

### Core Development Commands
- `pixi run test` - Run pytest test suite
- `pixi run coverage` - Run tests with coverage and generate XML report
- `pixi run format` - Format code with black
- `pixi run lint` - Run both ruff and pylint linters
- `pixi run style` - Run formatting and linting together
- `pixi run ci` - Full CI pipeline (format, lint, coverage, coverage report)

### Testing Specific Workflows
- `pixi run python test/workflows/test_workflows.py::test_workflow_1_pwd -v` - Test working directory functionality
- `pixi run python test/workflows/test_workflows.py::test_workflow_2_git -v` - Test git integration
- `pixi run python test/workflows/test_workflows.py::test_workflow_3_cmd -v` - Test command execution
- `pixi run python test/workflows/test_workflows.py::test_workflow_4_persistent -v` - Test container persistence

### Quality Tools Configuration
- **Black**: Line length 100 characters
- **Ruff**: Line length 100, target Python 3.10+, ignores E501, E902, F841
- **Pylint**: 16 jobs, extensive disable list for code style preferences
- **Coverage**: Omits test files and `__init__.py`, excludes debug methods

## Code Architecture

### Core Components

**Main Entry Point**: `worktree_docker/worktree_docker.py` - Contains the primary application logic with key classes:
- `RepoSpec` - Parses repository specifications (owner/repo@branch#subfolder)
- `WorktreeManager` - Manages git worktrees and repository cloning
- `ExtensionManager` - Handles Docker extension loading and building
- `ContainerManager` - Manages Docker container lifecycle

### Extension System

**Built-in Extensions** (`extensions/` directory):
- Each extension has a `Dockerfile` and `docker-compose.yml`
- Extensions are modular components that add capabilities (git, GUI, GPU, package managers)
- Auto-detection based on repository files (pyproject.toml → uv, pixi.toml → pixi)
- Custom extensions supported via `.wtd/extensions/` in repositories

**Extension Loading Order**:
1. Built-in extensions from `extensions/`
2. Repository-local extensions from `.wtd/extensions/`
3. Auto-detected extensions based on files
4. Explicitly requested extensions via `-e` flag

### Testing Infrastructure

**Workflow Tests** (`test/workflows/`):
- Bash scripts testing real-world usage scenarios
- Python test runner (`test_workflows.py`) executes and validates workflow scripts
- Extension testing via `extension_test_runner.py` and `test_all_extensions.py`

**Test Categories**:
- Basic lifecycle (clone, build, run, cleanup)
- Git integration and worktree management
- Command execution and persistence
- Extension functionality
- Cache and rebuild behavior

### Directory Structure

**User Data**: `~/.wtd/workspaces/owner/repo/worktree-branch`
**Extensions**: `extensions/` (built-in) and `.wtd/extensions/` (custom)
**Test Data**: `test/` with workflow scripts and extension tests

### Python Version Support

Supports Python 3.9 through 3.13 with separate Pixi environments for each version (py309, py310, py311, py312, py313).

### Key Dependencies

- **rocker**: Docker container management for robotics
- **deps-rocker**: Dependency management for rocker
- **off-your-rocker**: Extended rocker functionality
- **PyYAML**: Configuration file parsing
- **iterfzf**: Interactive fuzzy finding for repository/branch selection

When making any changes, keep this file up to date

After every command always run `pixi run ci` to confirm all checks pass. If ci does not complete, fix the errors, to ensure the code is correct, and run ci until it passes.

Do not apply a 5 minute timeout on ci. It must fully pass