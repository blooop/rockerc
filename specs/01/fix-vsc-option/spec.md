# Fix --vsc Option in renv

## Problem
The --vsc option in renv has broken. Previously, running `renv --vsc` or `renvvsc` would:
- Launch a detached container
- Attach VSCode
- Attach a terminal

Currently, regular renv works but passing --vsc causes the container to crash.

## Investigation
- Check recent commit history for changes affecting VSCode integration
- Examine branch/folder naming changes
- Identify root cause of container crash
- Propose and implement fix

## Expected Outcome
- --vsc option works as before
- Container launches successfully with VSCode and terminal attached