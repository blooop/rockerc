# Implementation Plan

## Investigation
The issue is in the bash completion function at `renv.py:167-217`. The completion logic uses `compgen -W` to generate completions from a list of repos.

## Root Cause
When building the repo list on line 194, we're adding `$user/$repo` entries. The issue is likely:
1. There may be multiple repos with common prefixes (e.g., `test_renv-branch1`, `test_renv-branch2`)
2. Bash completes to the common prefix and adds `-` as a separator

## Fix
Update the completion logic to ensure clean repo name completion without trailing characters. The completion should add a space after the repo name by default, allowing users to type `@` if they want branch-specific completion.

## Testing
1. Install updated completion: `renv --install`
2. Source bashrc: `source ~/.bashrc`
3. Test completion: `renv blo`<tab>
4. Verify no trailing dash
