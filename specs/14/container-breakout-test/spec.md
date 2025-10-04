# Container breakout detection test

## Problem
When the `~/renv` directory is deleted while a container is running, rockerc needs to detect the "container breakout" condition and automatically rebuild and reattach to a new container. Currently this works, but there's no automated test to ensure it continues working.

## Solution

Create `test_workflow_7_container_breakout.sh` that:
1. Runs `renv blooop/test_renv pwd` (serially)
2. Deletes the `~/renv` directory
3. Runs `renv blooop/test_renv pwd` again (serially)
4. Verifies that rockerc prints about container breakout and renv rebuilds the container

## Expected behavior
```bash
# First run - creates container
renv blooop/test_renv pwd

# Delete renv directory
rm -rf ~/renv

# Second run - should detect breakout and rebuild
renv blooop/test_renv pwd
# Should see: "Container appears corrupted (possible breakout detection), launching new container"
# Should successfully attach to new container
```

## Success criteria
- Test script runs without errors
- Container breakout is detected on second run
- New container is created and user is attached successfully
