from rockerc.rockerc import render_extension_table


def test_three_table_grouping_with_blacklist(capsys):
    """Validate three-table output: Global-only, Shared, Local-only.

    Blacklisted extensions stay in their table with status styling.
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
    # Headers must appear (in this order if groups present)
    g_idx = text.index("Global-only Extensions:")
    s_idx = text.index("Shared Extensions:")
    l_idx = text.index("Local-only Extensions:")
    assert g_idx < s_idx < l_idx
    # Each name confined to its table block (simple positional checks)
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
