# Container breakout detection test

## Problem
When the `~/renv` directory is deleted while a container is running, rockerc needs to detect the "container breakout" condition and automatically rebuild and reattach to a new container. Currently this works, but there's no automated test to ensure it continues working.

## Solution
Create `test_workflow_7_container_breakout.sh` that:
1. Creates and attaches to a container
2. Exits the container
3. Deletes the `~/renv` directory
4. Runs `renv` again with the same repo
5. Verifies that rockerc detects the container breakout and successfully rebuilds/reattaches

## Expected behavior
```bash
# First run - creates container
renv blooop/test_renv
exit

# Delete renv directory
rm -rf ~/renv

# Second run - should detect breakout and rebuild
renv blooop/test_renv
# Should see: "Container appears corrupted (possible breakout detection), launching new container"
# Should successfully attach to new container
```

## Success criteria
- Test script runs without errors
- Container breakout is detected on second run
- New container is created and user is attached successfully
