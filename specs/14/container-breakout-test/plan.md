# Implementation Plan

## 1. Create test_workflow_7_container_breakout.sh

The test script will follow this workflow:

### Setup
```bash
#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

# Clean up any existing test containers
docker rm -f test_renv-main >/dev/null 2>&1 || true
```

### Test Steps

1. **First container creation**
   - Run `renv blooop/test_renv` to create initial container and branch copy
   - Verify container is created
   - Exit container immediately

2. **Simulate breakout scenario**
   - Delete the `~/renv` directory (simulates the breakout condition)
   - This removes the branch copy but leaves the container running

3. **Second run - breakout detection**
   - Run `renv blooop/test_renv` again
   - Capture output to verify detection message
   - Check for: "Container appears corrupted (possible breakout detection)"
   - Verify new container is launched successfully

4. **Verification**
   - Ensure user is attached to new container
   - Run a simple command to verify container is functional
   - Exit and cleanup

### Output verification
```bash
# Capture output and check for key messages
output=$(renv blooop/test_renv 2>&1 || true)
echo "$output" | grep -q "Container appears corrupted (possible breakout detection)" || {
    echo "ERROR: Container breakout not detected"
    exit 1
}
echo "✓ Container breakout detection test passed"
```

## 2. Integration with CI

The test will be added to the existing test suite and run as part of `pixi run ci`.

## 3. Cleanup

Ensure all test artifacts are cleaned up:
- Remove test containers
- Remove test renv directory
