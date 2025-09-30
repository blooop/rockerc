# Detect Changed Extensions

## Current Behavior
When a container exists, rockerc automatically attaches to it regardless of whether the extension configuration has changed since the container was created.

## New Behavior
Before attaching to an existing container, rockerc should:
1. Compare current extension configuration with the configuration used to create the existing container
2. If extensions differ, do NOT auto-attach
3. Require rebuild (manual or via `-f` flag) to apply new configuration

This prevents using a container with stale/incorrect extensions.
