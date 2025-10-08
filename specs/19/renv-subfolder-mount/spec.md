# Renv Subfolder Mount Fix

## Problem
`renv owner/repo@branch#path` currently exposes the repository root inside the container, so users see sibling folders instead of an isolated workspace for the requested subfolder. Additionally, each branch+folder combination must create a unique container to enable independent work on multiple subfolders within the same branch.

## Requirements
- Mount only the requested subfolder into `/workspaces/{container-name}` when sparse checkout is enabled.
- Keep git metadata functional so commits, pulls, and pushes still work inside the container.
- Preserve existing behaviour when no subfolder is specified.
- **Each branch+folder combination must create a unique container** with a unique name (e.g., `test_renv-branch1`, `test_renv-branch1-folder1`, `test_renv-branch1-folder1-folder2`).
- Ensure repeated runs with the same branch+folder combination reuse the same container without reintroducing parent folders.
- When creating a fresh branch copy, update from remote refs first and avoid wiring new branches to track the template/default branch unless it actually exists upstream.
- Fail fast with a clear error if the requested subfolder does not exist in the repository.
- Provide an automated workflow that confirms multiple `renv owner/repo@branch#path` calls with different subfolders create independent containers.
