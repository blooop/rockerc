# Refactor and bugfixes from code review

Address code review comments:
- Refactor manage_container and related logic for readability (helper functions, context manager, sparse-checkout helper).
- Fix legacy repo name parsing to handle multiple dashes.
- Add checks/warnings to legacy workspace migration to prevent overwriting data.
- Improve error handling in cwd restoration.
- Refactor volume binding logic for deduplication.
- Reduce complexity in build_rocker_config.
- Add/expand tests for branch setup (upstream), sparse-checkout, duplicate volumes, and avoid loops in tests.

## Problem
Rocker fails to start with AttributeError: 'NoneType' object has no attribute 'group' in the plugin loading system.
# Fix Rocker Plugin Loading Issue

## Problem
Rocker fails to start with AttributeError: 'NoneType' object has no attribute 'group' in the plugin loading system.

## Root Cause
The `claude-npm` entry point in deps_rocker has an invalid module path: `deps_rocker.extensions.claude-npm.claude_npm:ClaudeNpm`. Python module names cannot contain dashes, causing importlib.metadata to fail when parsing the module path with regex.

## Solution
Fix the invalid entry point specification in deps_rocker by:
1. Renaming the module directory from `claude-npm` to `claude_npm`
2. Updating the entry point to use the correct module path with underscores

## Status
✅ Fixed: Rocker now loads successfully with all plugins including claude-npm
