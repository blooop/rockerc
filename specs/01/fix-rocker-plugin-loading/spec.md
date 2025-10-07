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