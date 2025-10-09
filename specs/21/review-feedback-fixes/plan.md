## Plan

1. Update `rockerc.core` dataclass annotations and mount target defaults for clarity.
2. Adjust `rockerc.renv` username resolution to catch documented exceptions only.
3. Add targeted renv tests:
   - Ensure `cwd` args are purged when present.
   - Validate default mount target path generation and `USER` fallback.
   - Verify custom mount target overrides propagate through `manage_container`.
   - Stabilize username-dependent assertions via mocking.
4. Run `pixi run ci` and address failures.
