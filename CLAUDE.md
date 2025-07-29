# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

rockerc is a Python tool that provides a configuration-file approach to using [rocker](https://github.com/osrf/rocker) - a Docker container tool for robotics development. It reads `rockerc.yaml` configuration files and passes the arguments to rocker to simplify container management.

## Development Commands

This project uses [Pixi](https://pixi.sh) for package and environment management. All commands are defined in `pyproject.toml` under `[tool.pixi.tasks]`.

### Core Development Commands
- `pixi run test` - Run pytest test suite
- `pixi run coverage` - Run tests with coverage and generate XML report
- `pixi run format` - Format code with black
- `pixi run lint` - Run both ruff and pylint linters
- `pixi run style` - Run formatting and linting together
- `pixi run ci` - Full CI pipeline (format, lint, coverage, coverage report)

### Quality Tools Configuration
- **Black**: Line length 100 characters
- **Ruff**: Line length 100, target Python 3.10+, ignores E501, E902, F841
- **Pylint**: 16 jobs, extensive disable list for code style preferences
- **Coverage**: Omits test files and `__init__.py`, excludes debug methods

### Testing
- Uses pytest with hypothesis for property-based testing
- Test files located in `test/` directory
- Main test file: `test/test_basic.py`
- Workflow tests in `test/workflows/` directory

## Code Architecture

### Core Module: `rockerc/rockerc.py`

**Key Functions:**
- `yaml_dict_to_args(d: dict) -> str` - Converts YAML config to rocker command arguments
- `collect_arguments(path: str = ".") -> dict` - Searches for and merges rockerc.yaml files
- `build_docker(dockerfile_path: str = ".") -> str` - Builds Docker images from Dockerfiles
- `save_rocker_cmd(split_cmd: str)` - Generates Dockerfile.rocker and run_dockerfile.sh
- `run_rockerc(path: str = ".")` - Main entry point that orchestrates the workflow

**Configuration Flow:**
1. Searches for `rockerc.yaml` files in the specified path
2. Merges configurations if multiple files found
3. Handles special cases for dockerfile builds vs image pulls
4. Converts configuration to rocker command line arguments
5. Optionally generates Dockerfile and run script with `--create-dockerfile`

### Configuration Files

**rockerc.yaml structure:**
```yaml
image: ubuntu:22.04  # Base Docker image
# OR
dockerfile: Dockerfile  # Path to Dockerfile for building

args:  # List of rocker extensions/arguments
  - nvidia
  - x11
  - user
  - pull
  - deps
  - git
  - pixi
```

**rockerc.deps.yaml** - Defines dependencies for rocker extensions:
- `apt_tools` - System packages to install
- `pip_language-toolchain` - Python packages for development

## Special Behaviors

- If `dockerfile` is specified, automatically builds the image and removes `pull` from args
- The `--create-dockerfile` flag generates `Dockerfile.rocker` and `run_dockerfile.sh`
- Supports recursive search for multiple `rockerc.yaml` files
- Entry point script: `rockerc` command maps to `rockerc.rockerc:run_rockerc`

## Dependencies

**Runtime:**
- rocker>=0.2.17
- deps-rocker>=0.10  
- off-your-rocker>=0.1.0
- pyyaml>=5

**Development:** Comprehensive testing and linting stack including black, pylint, pytest, ruff, coverage, and hypothesis.

## Python Version Support

Supports Python 3.9 through 3.13 with separate Pixi environments for each version (py309, py310, py311, py312, py313).