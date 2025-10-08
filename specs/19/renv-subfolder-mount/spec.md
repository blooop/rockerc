# Renv Subfolder Mount Fix

## Problem
`renv owner/repo@branch#path` currently exposes the repository root inside the container, so users see sibling folders instead of an isolated workspace for the requested subfolder.

## Requirements
- Mount only the requested subfolder into `/workspaces/{container-name}` when sparse checkout is enabled.
- Keep git metadata functional so commits, pulls, and pushes still work inside the container.
- Preserve existing behaviour when no subfolder is specified.
- Ensure repeated runs reuse caches/containers without reintroducing parent folders.
- When creating a fresh branch copy, update from remote refs first and avoid wiring new branches to track the template/default branch unless it actually exists upstream.
- Fail fast with a clear error if the requested subfolder does not exist in the repository.
- Provide an automated workflow that confirms `renv owner/repo@branch#path` runs against a clean `RENV_DIR` and lands in the requested subfolder workspace.
- **BUG**: When a branch container already exists (e.g., `renv owner/repo@branch1`), subsequent subfolder checkouts on the same branch (e.g., `renv owner/repo@branch1#folder1`) must correctly mount and set the working directory to the subfolder. Currently, the working directory stays at the root when reusing existing branch containers.
