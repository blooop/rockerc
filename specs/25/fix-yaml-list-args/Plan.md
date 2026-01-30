# Plan: Fix YAML List Arguments Expansion

**Issue:** [#120 (comment #3824380588)](https://github.com/blooop/rockerc/issues/120#issuecomment-3824380588)

## Problem

When specifying multiple positional arguments as a YAML list, the values are incorrectly converted to a Python list string representation instead of being expanded as separate arguments.

**Example input (rockerc.yaml):**
```yaml
devices:
  - /dev/dri
  - /dev/ttyACM0
```

**Current (broken) output:**
```
rocker --x11 --user --home --devices [/dev/dri, /dev/ttyACM0]
```

**Expected output:**
```
rocker --x11 --user --home --devices /dev/dri --devices /dev/ttyACM0
```

## Root Cause

The bug is in `rockerc/rockerc.py` at lines 354-355 in the `yaml_dict_to_args` function:

```python
# key/value pairs
for k, v in d.items():
    segments.extend([f"--{k}", str(v)])
```

When `v` is a list, `str(v)` produces `"['/dev/dri', '/dev/ttyACM0']"` instead of expanding each list item into a separate `--devices <value>` argument.

## Solution

Modify the `yaml_dict_to_args` function to handle list values by expanding them into repeated flags:

```python
# key/value pairs
for k, v in d.items():
    if isinstance(v, list):
        # Expand list into repeated flags: --devices /dev/dri --devices /dev/ttyACM0
        for item in v:
            segments.extend([f"--{k}", str(item)])
    else:
        segments.extend([f"--{k}", str(v)])
```

## Implementation Steps

1. **Modify `yaml_dict_to_args` function** (rockerc/rockerc.py:354-355)
   - Add check for list-type values
   - Expand list items into repeated flags

2. **Add unit tests**
   - Test single value (existing behavior)
   - Test list of values (new behavior)
   - Test empty list
   - Test mixed config with both single and list values

3. **Update documentation/examples**
   - Add an example showing multiple devices in intel-gpu.yaml or a new example
   - Document the list syntax for key/value pairs

4. **Run CI and verify**
   - Ensure all existing tests pass
   - Verify the fix works with real rocker commands

## Test Cases

```python
def test_yaml_dict_to_args_list_expansion():
    """List values should expand into repeated flags."""
    d = {"devices": ["/dev/dri", "/dev/ttyACM0"], "image": "ubuntu:24.04"}
    result = yaml_dict_to_args(d.copy())
    assert "--devices /dev/dri --devices /dev/ttyACM0" in result

def test_yaml_dict_to_args_single_value():
    """Single values should work as before."""
    d = {"devices": "/dev/dri", "image": "ubuntu:24.04"}
    result = yaml_dict_to_args(d.copy())
    assert "--devices /dev/dri" in result
```

## Affected Files

- `rockerc/rockerc.py` - Main fix location
- `test/test_basic.py` or new test file - Add tests
- `examples/intel-gpu.yaml` or new example - Documentation

## Alternative Approaches Considered

1. **Space-separated values in single flag:** `--devices /dev/dri /dev/ttyACM0`
   - Rejected: Not all CLI flags support this format

2. **Comma-separated values:** `--devices /dev/dri,/dev/ttyACM0`
   - Rejected: Rocker uses repeated flags for multiple values

3. **Chosen approach: Repeated flags**
   - Matches standard CLI convention
   - Works with how rocker CLI expects multiple values
