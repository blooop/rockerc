# Tab Completion Trailing Dash Fix

## Problem
Tab completion for renv repo names adds a trailing dash (e.g., `renv blooop/test_renv-`) when it should complete without it (e.g., `renv blooop/test_renv`).

## Solution
Modify bash completion logic in `renv.py` to:
1. Complete repo names without trailing characters
2. Allow user to manually type `@` to specify branch if needed

## Expected Behavior
- `renv blo`<tab> → `renv blooop/test_renv` (no trailing characters)
- User can immediately type `@` to get branch completions
