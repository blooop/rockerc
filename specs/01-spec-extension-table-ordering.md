# Spec: Extension Table Ordering

## User Requirement (Initial Instruction)
Row Group Ordering (strict):

1. Global-only: in `original_global_args`, not in `original_project_args`
2. Shared: in both `original_global_args` and `original_project_args`
3. Local-only: in `original_project_args`, not in `original_global_args`

Blacklisted extensions: Any blacklisted extension that fits one of the above categories still appears in its natural group. Do **not** create a separate blacklist group.

## Acceptance Criteria
- Output table rows appear strictly in the order of the three groups above.
- Within each group, preserve existing sort behavior (describe current behavior once code is inspected) or apply alphabetical ordering if none exists.
- No additional grouping header for blacklisted items.
- Tests (existing or new) reflect this ordering.

## Open Questions / To Confirm
- How are blacklisted extensions currently marked? (Field name?)
- Existing table sort order within a group.
- Where the table is generated (suspect `rockerc/core.py` or `rockerc/rockerc.py`).

## Implementation Plan (Initial)
1. Identify data structure holding `original_global_args` and `original_project_args`.
2. Compute membership categories with set operations.
3. Filter/retain blacklisted flag but leave ordering determined solely by group sequence.
4. Concatenate lists in the required order when rendering.
5. Update or add tests to assert ordering.

## Risks
- Hidden dependency on previous ordering in other tests.
- Blacklist handling logic may currently prune items (need to ensure not dropping them).

## Next Steps
- Inspect code generating extension table.
- Implement grouping logic.
- Adjust tests if needed.

## Implementation Notes (2025-09-29)
Implemented in `render_extension_table` (already present) which already followed required grouping order. Added new test `test_extension_table_ordering.py` to assert:

- Ordering: Global-only -> Shared -> Local-only.
- Blacklisted extensions (`shared1`, `local2` in the test) appear in-place with status `blacklisted` and no separate grouping label.
- Test enforces relative ordering using substring indices in captured output.

Edge cases handled in code:
- Aggregated token expansion (`nvidia - x11 - user`) already normalizes before grouping.
- Defensive insertion of any `removed_by_blacklist` extension not originally present preserves correct group inferred from provenance.

No code changes were required for ordering; only the test enforcing the spec was added.

All tests pass: 43 passed, 1 skipped (see CI run).
