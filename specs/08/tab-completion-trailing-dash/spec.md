# Tab Completion and Cache Location Fix

## Problems
1. Tab completion adds trailing space after repo name
2. Cache directories visible in ~/renv/{owner}/ directory listings
3. Branch completion after @ not working

## Solution
1. Move cache from `~/renv/{owner}/{repo}-cache` to `~/renv/.cache/{owner}/{repo}`
2. Update completion to use nospace and properly handle branch completion
3. Parse repo name from current word when @ is present

## Expected Behavior
- `renv blo`<tab> → `renv blooop/test_renv` (no trailing space)
- `renv blooop/test_renv@`<tab> → shows available branches
- Cache hidden in `~/renv/.cache/` (starts with dot)
