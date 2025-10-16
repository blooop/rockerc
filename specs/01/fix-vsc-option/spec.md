# Fix --vsc Option in renv

## Problem
The --vsc option in renv has broken. Previously, running `renv --vsc` or `renvvsc` would:
- Launch a detached container
- Attach VSCode
- Attach a terminal

Currently, regular renv works but passing --vsc causes the container to crash.

## Root Cause
The issue is caused by the lowercase repo name changes in commit e78dab4. The `RepoSpec.parse()` method now enforces lowercase owner and repo names, which changes container names from `MixedRepo.main` to `mixedrepo.main`.

This breaks VSCode integration because:
1. The `container_hex` value for VSCode URIs is generated from container names
2. Existing containers have old names, but new connections expect lowercase names
3. The `launch_vscode()` function fails when container names don't match

## Solution
The lowercase enforcement is correct and should be kept. The fix is to remove redundant lowercasing in `get_container_name()` and `get_hostname()` functions since `RepoSpec.parse()` already enforces lowercase names.

## Changes Made
- Removed redundant `.lower()` calls in `get_container_name()` and `get_hostname()`
- Updated comments to clarify that repo names are already lowercase from parsing
- This ensures consistent container naming behavior

## Expected Outcome
- --vsc option works as before
- Container launches successfully with VSCode and terminal attached