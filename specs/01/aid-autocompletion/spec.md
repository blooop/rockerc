# aid autocompletion

## Summary
Add shell autocompletion support to the `aid` CLI. Manage installation centrally via `rockerc --install`, ensuring completions are refreshed every run.

## Requirements
- Implement shell autocompletion for `aid` (bash, zsh, fish if possible).
- Ensure `rockerc --install` always installs/updates the completion script file, overwriting any previous version.
- Write all completion definitions to a single installed file and have shell configs source that file rather than inlining large blocks.
- Keep autocompletion commands hidden behind `rockerc --install` so the `aid` and `renv` CLIs avoid extra flags.
- The generated completion script must be valid shell code (no extra escaping or syntax errors) so sourcing it succeeds on bash.
- Keep implementation concise and robust.
- Update tests if needed.
