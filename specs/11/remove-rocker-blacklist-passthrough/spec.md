# Remove extension-blacklist passthrough to rocker

## Problem
Rockerc filters blacklisted extensions from args but also passes `--extension-blacklist` to rocker, causing errors when rocker implicitly adds blacklisted extensions via dependencies.

## Solution
Remove extension-blacklist from being passed to rocker. Keep it as internal rockerc filtering only.

## Implementation
Remove the extension-blacklist handling in `yaml_dict_to_args()` function in rockerc.py (lines 295-302).
