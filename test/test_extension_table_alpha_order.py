from rockerc.rockerc import render_extension_table


def test_group_precedence_with_stable_intragroup_order(capsys):
    """Validate precedence sorting (global-only -> shared -> local-only) with stable original order.

    We shuffle raw order so that some global-only entries appear AFTER shared/local in source lists
    to ensure they are lifted ahead in final ordering while preserving their internal order.

    global args raw: g2, shared1, g1, shared2
    project args raw: shared2, local2, shared1, local1

    Provenance groups:
      global-only: g2, g1   (order from first appearance in concatenated lists)
      shared:      shared1, shared2  (first appearances)
      local-only:  local2, local1

    Final expected sequence: g2, g1, shared1, shared2, local2, local1
    """

    original_global_args = ["g2", "shared1", "g1", "shared2"]
    original_project_args = ["shared2", "local2", "shared1", "local1"]
    blacklist = []
    removed = []
    # Final args (post-merge, no blacklist filtering) approximated; actual order is not used for sorting now.
    final_args = ["g2", "shared1", "g1", "shared2", "local2", "local1"]

    render_extension_table(
        final_args,
        original_global_args=original_global_args,
        original_project_args=original_project_args,
        blacklist=blacklist,
        removed_by_blacklist=removed,
    )

    out = capsys.readouterr().out
    expected_sequence = ["g2", "g1", "shared1", "shared2", "local2", "local1"]
    positions = {name: out.index(name) for name in expected_sequence}
    assert (
        positions["g2"]
        < positions["g1"]
        < positions["shared1"]
        < positions["shared2"]
        < positions["local2"]
        < positions["local1"]
    )


def test_duplicate_extension_names_in_input_lists(capsys):
    """Verify table behavior when duplicate extension names are in input lists.

    Duplicates should be deduplicated, with each extension appearing once in its
    appropriate group.
    """
    original_global_args = ["shared1", "gonly", "shared1", "gonly"]
    original_project_args = ["shared1", "local1", "shared1", "local1"]
    blacklist = []
    removed = []
    final_args = ["shared1", "gonly", "local1"]

    render_extension_table(
        final_args,
        original_global_args=original_global_args,
        original_project_args=original_project_args,
        blacklist=blacklist,
        removed_by_blacklist=removed,
    )

    out = capsys.readouterr().out
    lines = out.splitlines()
    # Each extension should appear in exactly one ROW (though shared1 appears in 2 columns)
    # Count rows containing each extension
    gonly_rows = [line for line in lines if "gonly" in line]
    shared1_rows = [
        line for line in lines if "shared1" in line and "Status" not in line
    ]  # exclude header
    local1_rows = [line for line in lines if "local1" in line]

    assert len(gonly_rows) == 1, f"Expected 1 row with gonly, got {len(gonly_rows)}"
    assert len(shared1_rows) == 1, f"Expected 1 row with shared1, got {len(shared1_rows)}"
    assert len(local1_rows) == 1, f"Expected 1 row with local1, got {len(local1_rows)}"

    # Verify grouping order: global-only (gonly) < shared (shared1) < local-only (local1)
    positions = {
        "gonly": out.index("gonly"),
        "shared1": out.index("shared1"),
        "local1": out.index("local1"),
    }
    assert positions["gonly"] < positions["shared1"] < positions["local1"]
