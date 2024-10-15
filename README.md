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

```
pip install rockerc
```

## Usage

```
#searches for rockerc.yaml and passes those arguments to rocker
rockerc 
```

## Motivation

[Rocker](https://github.com/osrf/rocker) is an alternative to docker-compose that makes it easier to run containers with access to features of the local environment and add extra capabilities to existing docker images.  However rocker has many configurable options and it can get hard to read or reuse those arguments.  This is a naive wrapper that read a rockerc.yaml file and passes them to rocker.  There are currently [no plans](https://github.com/osrf/rocker/issues/148) to integrate docker-compose like functionalty directly into rocker so I made this as a proof of concept to see what the ergonomics of it would be like. 

## Caveats

I'm not sure this is the best way of implementing rockerc like functionality.  It might be better to implmented it as a rocker extension, or in rocker itself.  This was just the simplest way to get started. I may explore those other options in more detail in the future. 
