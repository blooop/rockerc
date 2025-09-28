# rockerc

## Continuous Integration Status

[![Ci](https://github.com/blooop/rockerc/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/blooop/rockerc/actions/workflows/ci.yml?query=branch%3Amain)
[![Codecov](https://codecov.io/gh/blooop/rockerc/branch/main/graph/badge.svg?token=Y212GW1PG6)](https://codecov.io/gh/blooop/rockerc)
[![GitHub issues](https://img.shields.io/github/issues/blooop/rockerc.svg)](https://GitHub.com/blooop/rockerc/issues/)
[![GitHub pull-requests merged](https://badgen.net/github/merged-prs/blooop/rockerc)](https://github.com/blooop/rockerc/pulls?q=is%3Amerged)
[![GitHub release](https://img.shields.io/github/release/blooop/rockerc.svg)](https://GitHub.com/blooop/rockerc/releases/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/rockerc)](https://pypistats.org/packages/rockerc)
[![License](https://img.shields.io/github/license/blooop/rockerc)](https://opensource.org/license/mit/)
[![Python](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/downloads/)
[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)

## Installation

### Recommended Method:

Install [pipx](https://pypa.github.io/pipx/) (if not already installed):

```
sudo apt install pipx
pipx ensurepath
```

Then install rockerc and its dependencies globally with:

```
pipx install --include-deps rockerc
```

to develop run
```
pipx install --include-deps . --force
```

This will ensure that `rockerc` and `rocker` commands are available on your PATH.

## Architecture

rockerc follows a layered architecture designed for maximum code reuse between terminal and VSCode workflows:

### Base Layer
- **rockerc**: Core container management tool that reads `rockerc.yaml` files and launches containers
- **rockervsc**: Light wrapper that shares rockerc functionality, adds VSCode integration

### Environment Layer
- **renv**: Multi-repository environment manager that collects configuration arguments and uses rockerc functions
- **renvvsc**: Functions the same as renv, but uses rockervsc functions for VSCode integration

### Benefits of this Architecture
- **Maximum code reuse**: Changes in core functionality automatically benefit both terminal and VSCode workflows
- **Consistent interfaces**: All tools share the same command-line interface and configuration format
- **Easy maintenance**: Bug fixes and features only need to be implemented once in the base layer
- **Shared Python code**: Components call each other via Python functions rather than command line, ensuring efficient execution and consistent behavior

This design ensures that whether you're using terminal-based development or VSCode integration, you get the same robust container management with your preferred interface.

## Usage

navigate to a directory with a `rockerc.yaml` file and run:
```
rockerc
```

This will search recursively for rockerc.yaml and pass those arguments to rocker

### VS Code Integration

For automatic VS Code integration, use `rockervsc` instead:
```
rockervsc
```

`rockervsc` functions the same as `rockerc` but will automatically launch and attach VS Code to the created container. This provides seamless development environment setup with VS Code running inside your rocker container.

`rockervsc` forwards all arguments to `rockerc`, so you can use any `rockerc` options:
```
rockervsc --gemini
```

The command will:
1. Run `rockerc` with your arguments plus container configuration for VS Code
2. Launch VS Code and attach it to the container
3. If the container already exists, it will just attach VS Code without recreating it

For multi-repository development with git worktrees and VS Code, use `renvsc`:
```
renvsc owner/repo@branch
```

`renvsc` combines the full functionality of `renv` (repository and worktree management) with automatic VS Code integration. See [renv.md](renv.md) for complete documentation.

## Motivation

[Rocker](https://github.com/osrf/rocker) is an alternative to docker-compose that makes it easier to run containers with access to features of the local environment and add extra capabilities to existing docker images.  However rocker has many configurable options and it can get hard to read or reuse those arguments.  This is a naive wrapper that read a rockerc.yaml file and passes them to rocker.  There are currently [no plans](https://github.com/osrf/rocker/issues/148) to integrate docker-compose like functionality directly into rocker so I made this as a proof of concept to see what the ergonomics of it would be like. 

## Caveats

I'm not sure this is the best way of implementing rockerc like functionality.  It might be better to implemented it as a rocker extension, or in rocker itself.  This was just the simplest way to get started. I may explore those other options in more detail in the future. 


# rocker.yaml configuration

You need to pass either a docker image, or a relative path to a dockerfile

rockerc.yaml
```yaml
image: ubuntu:22.04
```

or

```yaml
dockerfile: Dockerfile
```

will look for the dockerfile relative to the rockerc.yaml file
