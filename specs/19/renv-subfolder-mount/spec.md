# Renv Subfolder Mount Fix

## Problem
`renv owner/repo@branch#path` currently exposes the repository root inside the container, so users see sibling folders instead of an isolated workspace for the requested subfolder.

## Requirements
- Mount only the requested subfolder into `/workspaces/{container-name}` when sparse checkout is enabled.
- Keep git metadata functional so commits, pulls, and pushes still work inside the container.
- Preserve existing behaviour when no subfolder is specified.
- Ensure repeated runs reuse caches/containers without reintroducing parent folders.
