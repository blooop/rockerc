# aid autocompletion

## Summary
Add shell autocompletion support to the `aid` CLI. Update the `autocomplete --install` function so it always installs the latest version, even if autocompletion is already present.

## Requirements
- Implement shell autocompletion for `aid` (bash, zsh, fish if possible).
- Ensure `aid autocomplete --install` always installs/updates the completion script, overwriting any previous version.
- Write all completion definitions to a single installed file and have shell configs source that file rather than inlining large blocks.
- Keep implementation concise and robust.
- Update tests if needed.
