# Submodule Support for Reference Cache Repos

## Problem
When repositories contain git submodules, the reference cache repo and branch copies don't properly initialize or update them, leading to incomplete working trees.

## Solution
1. Clone cache repos with `--recurse-submodules` flag
2. Pull latest changes before setting up new branch copies
3. Update submodules with `git submodule update --recursive --init` after pulling

## Changes
- `setup_cache_repo()`: Add `--recurse-submodules` to initial clone
- `setup_cache_repo()`: Replace `fetch --all` with `pull` to update working tree
- `setup_cache_repo()`: Add submodule update after pull
