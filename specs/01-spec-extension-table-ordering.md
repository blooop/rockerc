# Spec: Extension Table Ordering

## User Requirement (Initial Instruction)
Row Group Ordering (strict):

1. Global-only: in `original_global_args`, not in `original_project_args`
2. Shared: in both `original_global_args` and `original_project_args`
3. Local-only: in `original_project_args`, not in `original_global_args`

Blacklisted extensions: Any blacklisted extension that fits one of the above categories still appears in its natural group. Do **not** create a separate blacklist group.

## Clarification 2025-09-29: Remove Redundant Column
The current table prints columns: Global | Local | Extension | Status.
The 'Extension' column is redundant (it duplicates the non-empty cell from Global/Local context).

Update: Remove the 'Extension' column. New columns: Global | Local | Status.
Display extension names only in the provenance columns (Global/Local) where they apply; a row will still show both cells populated for shared extensions.
For global-only or local-only extensions the non-applicable cell remains blank.
Status coloring & blacklist strike-through remains unchanged.

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

### Update 2025-09-29 (Column Removal Implemented)
Removed the redundant 'Extension' column from `render_extension_table`:
- Adjusted docstring & headers to `Global | Local | Status`.
- Row construction now appends only three cells.
- Updated ordering test to assert absence of the word 'Extension' in header line.
- CI after change: 43 passed, 1 skipped.

### Clarification 2025-09-29 (Provenance Sorting Reinforced)
Per latest instruction: The table MUST be sorted strictly by provenance groups, in this exact sequence:
1. Global-only (extension appears only in Global column)
2. Shared (appears in both Global and Local columns)
3. Local-only (appears only in Local column)

Within each group we retain the original (stable) encounter order taken from the source argument lists; no additional alphabetical sort is applied unless a future requirement states otherwise. This matches current implementation (`render_extension_table`) which constructs `global_only + shared + local_only` in that order.
