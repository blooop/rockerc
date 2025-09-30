# Extension Table Split Construction (Spec)

Goal: Build three separate tables (global-only, shared, local-only) as in-memory row arrays, then vertically concatenate (global, shared, local) before converting to formatted text output. Avoid incremental text concatenation logic during classification.

Requirements:
- Inputs: final_args, original_global_args, original_project_args, blacklist, removed_by_blacklist.
- Classify each unique extension into exactly one provenance group: global-only, shared, local-only.
- Produce three independent row arrays with columns [Global, Local, Status]. Empty cells rendered as empty string.
- Apply blacklist/removed status styling per existing logic.
- After arrays built, concatenate: combined_rows = global_rows + shared_rows + local_rows.
- Render once with tabulate using headers [Global, Local, Status] for each group section OR (if required by tests) keep current per-section headings but ensure each section's rows derived from its own array. (Current tests expect separate titled sections.)
- Do NOT perform ordering or status decisions while rendering text; all logic happens while building arrays.
- Preserve current ordering semantics: group precedence (global-only, shared, local-only) with stable first-seen order inside each group. Reinstate blacklisted entries into proper group even if removed from final_args.
- Maintain aggregate token expansion prior to grouping.

Success Criteria:
- All existing extension table tests pass unmodified.
- Implementation uses pure array assembly before any string formatting.
- No regression in color/strike formatting behavior.

Edge Cases:
- Empty group(s) omitted from output.
- Aggregated tokens ("a - b - c") expanded before classification.
- Blacklisted extension absent from provenance lists: still appears in correct relative group ordering.

Out of Scope:
- Changing column names or adding new provenance columns.
- Altering color codes or test expectations.
