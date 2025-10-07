# Implementation Plan

## Issue Analysis
The error occurs in `/home/ags/.venvs/dev-tools-uv/lib/python3.12/site-packages/rocker/core.py:510` when `entry_point.load()` is called for the `claude-npm` extension from deps_rocker.

The entry point specification:
```
EntryPoint(name='claude-npm', value='deps_rocker.extensions.claude-npm.claude_npm:ClaudeNpm', group='rocker.extensions')
```

The problem is that `claude-npm` in the module path contains a dash, which is invalid in Python module names. When importlib.metadata tries to parse this with regex, it returns None, causing the AttributeError.

## Solution Steps
1. **Check if deps_rocker is an editable install** - If it's installed in development mode, we can fix it directly
2. **Locate the entry point definition** - Find where this entry point is defined in deps_rocker
3. **Fix the module path** - Change `deps_rocker.extensions.claude-npm.claude_npm` to `deps_rocker.extensions.claude_npm.claude_npm`
4. **Verify the module exists** - Ensure the actual module path matches the corrected entry point
5. **Test the fix** - Verify rocker can load all plugins successfully

## Files to Check
- deps_rocker's pyproject.toml or setup.py for entry point definitions
- deps_rocker's module structure to verify correct paths
- Test rocker startup after fix

## Alternative Solutions
If deps_rocker is not editable:
1. Create a workaround in rockerc to filter out problematic entry points
2. Report the issue upstream to deps_rocker maintainers
3. Pin to a working version of deps_rocker if available