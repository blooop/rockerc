# Implementation Plan

## Overview
Change the `-f` flag behavior from renaming containers to stopping and rebuilding them.

## Steps

1. **Locate the `-f` flag handling code**
   - Find where the force flag is processed
   - Identify the container rename logic

2. **Replace rename logic with stop + rebuild**
   - Stop the existing container instead of renaming
   - Proceed with rebuild as normal
   - Ensure proper error handling for both operations

3. **Update tests**
   - Modify existing tests that expect rename behavior
   - Ensure tests verify stop + rebuild behavior

4. **Run CI**
   - Execute `pixi run ci`
   - Fix any failures
   - Iterate until passing

## Technical Notes
- Need to ensure container is properly stopped before rebuild
- Handle cases where container might not exist or is already stopped
- Verify cleanup happens correctly
