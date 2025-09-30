# Force Flag Rebuild Behavior

## Current Behavior
When using `-f` flag, the system renames the existing container.

## New Behavior
When using `-f` flag, the system should:
1. Stop the existing container
2. Rebuild it from scratch

This ensures a clean rebuild without relying on container renaming.
