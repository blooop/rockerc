from rockerc.rockerc import render_extension_table


def test_three_table_grouping_with_blacklist(capsys):
    """Validate single concatenated table output: Global-only, Shared, Local-only rows in sequence.

    Blacklisted extensions stay in their group position with status styling.
    """

    original_global_args = ["gonly", "shared1", "shared2"]
    original_project_args = ["shared1", "local1", "shared2", "local2"]
    blacklist = ["shared1", "local2"]
    removed = ["shared1", "local2"]
    final_args = ["gonly", "shared2", "local1"]

    render_extension_table(
        final_args,
        original_global_args=original_global_args,
        original_project_args=original_project_args,
        blacklist=blacklist,
        removed_by_blacklist=removed,
    )
    out = capsys.readouterr().out.splitlines()
    text = "\n".join(out)

    # Should have table headers but no section titles
    assert "Global" in text and "Local" in text and "Status" in text
    assert "Global-only Extensions:" not in text
    assert "Shared Extensions:" not in text
    assert "Local-only Extensions:" not in text

    # Each name appears in the correct group order (global-only, shared, local-only)
    gonly_pos = text.index("gonly")
    shared1_pos = text.index("shared1")
    shared2_pos = text.index("shared2")
    local1_pos = text.index("local1")
    local2_pos = text.index("local2")
    assert gonly_pos < shared1_pos < shared2_pos < local1_pos < local2_pos

    # Blacklisted entries present and marked
    assert "blacklisted" in text

    # Deprecated standalone heading 'Extensions:' (without qualifier) must not appear
    assert "\nExtensions:\n" not in f"\n{text}\n"


def test_blacklist_only_extension_grouping(capsys):
    """Test edge case: extension present only in blacklist, not in args.

    Verifies correct table rendering and grouping for blacklist-only extension.
    """
    original_global_args = ["gonly", "shared1", "shared2"]
    original_project_args = ["shared1", "local1", "shared2", "local2"]
    blacklist = ["shared1", "local2", "blacklist_only_ext"]
    removed = ["shared1", "local2"]
    final_args = ["gonly", "shared2", "local1"]

    render_extension_table(
        final_args,
        original_global_args=original_global_args,
        original_project_args=original_project_args,
        blacklist=blacklist,
        removed_by_blacklist=removed,
        original_global_blacklist=["blacklist_only_ext"],
    )

    out = capsys.readouterr().out
    # blacklist_only_ext is not present in args, only in blacklist
    assert "blacklist_only_ext" not in original_global_args
    assert "blacklist_only_ext" not in original_project_args
    # But it should appear in the output (in the Global column with filtered/blacklisted status)
    assert "blacklist_only_ext" in out
    # Verify it has appropriate status marking
    assert "filtered" in out or "blacklisted" in out
