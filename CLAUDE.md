# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

worktree_docker is a Python tool that provides a configuration-file approach to using [rocker](https://github.com/osrf/rocker) - a Docker container tool for robotics development. It reads `worktree_docker.yaml` configuration files and passes the arguments to rocker to simplify container management.

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


**Development:** Comprehensive testing and linting stack including black, pylint, pytest, ruff, coverage, and hypothesis.

## Python Version Support

Supports Python 3.9 through 3.13 with separate Pixi environments for each version (py309, py310, py311, py312, py313).