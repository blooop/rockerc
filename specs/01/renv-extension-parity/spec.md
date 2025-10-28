# renv Extension Argument Parity

## Summary
- Allow `renv` to accept the same extension-selection CLI arguments supported by `rockerc`.
- Ensure wrapper entrypoints (`renvvsc`, `rockervsc`) retain consistent behavior.
- Preserve existing defaults when no explicit extension flags are provided.

## Acceptance Criteria
- `renv` accepts the full set of extension-related flags that `rockerc` supports today.
- Passing any of these flags to `renv` yields the same extension resolution as invoking `rockerc` with the same flags.
- Wrapper commands continue to match their base command behavior without regressions.
- Automated tests cover the shared parsing surface and enforce parity for future changes.
- `pixi run ci` passes.
