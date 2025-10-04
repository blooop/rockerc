# Implementation Plan

## Current Behavior
1. rockerc collects extension-blacklist from global and project configs
2. Filters blacklisted extensions from args list (correct)
3. Passes filtered args to rocker (correct)
4. **Also passes --extension-blacklist to rocker (incorrect)**

## Root Cause
When an extension like `pixi` implicitly requires a blacklisted extension like `nvidia`, rocker adds it but then errors because nvidia is in the blacklist.

## Changes Required

### 1. Remove extension-blacklist passthrough in yaml_dict_to_args()
File: `rockerc/rockerc.py` lines 295-302

Remove this code block:
```python
# special handling for extension-blacklist
extension_blacklist = d.pop("extension-blacklist", None)
if extension_blacklist:
    if isinstance(extension_blacklist, list):
        for extension in extension_blacklist:
            segments.extend(["--extension-blacklist", str(extension)])
    else:
        segments.extend(["--extension-blacklist", str(extension_blacklist)])
```

Replace with just:
```python
# Remove extension-blacklist - it's only for internal rockerc filtering
d.pop("extension-blacklist", None)
```

### 2. Update tests
Remove or update tests that expect `--extension-blacklist` in rocker command output:
- `test_extension_blacklist_with_list` (line 192)
- `test_extension_blacklist_with_multiple_items` (line 202)
- `test_extension_blacklist_with_single_string` (line 208)
- `test_extension_blacklist_with_no_args` (line 214)

These tests should verify that blacklisted extensions are NOT in args, rather than checking for --extension-blacklist flag.

## Expected Outcome
- Blacklisted extensions are filtered from args before passing to rocker
- Rocker never receives --extension-blacklist flag
- Rocker can freely add implicit dependencies without blacklist conflicts
