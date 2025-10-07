# Monorepo Subfolder Isolation

## Problem
When working with monorepos, users need to check out and work with isolated subfolders without seeing or accessing parent folders from inside the container. Current implementation mounts the entire repo even when a subfolder is specified.

## Requirements
- Support syntax: `owner/repo@branch#folder/subfolder` to check out only the specified subfolder
- Inside the container, the subfolder should appear at the workspace root (`/workspaces/{container-name}`)
- Git must function normally (commit, push, pull) from within the subfolder
- User cannot see parent folders from inside the container
- Changes committed in the container appear normally in the parent repo
- The host filesystem maintains the full repo structure with sparse checkout

## Solution
Use git sparse-checkout to:
1. Clone the full repo to cache (as currently done)
2. In the branch copy, initialize sparse-checkout to only check out the specified subfolder
3. Mount only the checked-out subfolder into the container at the workspace root
4. Git operations work normally since the .git directory contains all necessary metadata
