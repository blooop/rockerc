from rockerc.rockerc import render_extension_table


def test_concatenated_group_order_with_blacklist(capsys):
    """Validate single-table concatenated ordering: Global-only -> Shared -> Local-only.

    No group titles should appear; ordering enforced solely by row sequence.
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
    text = capsys.readouterr().out
    # Ensure no group headers
    assert "Global-only Extensions:" not in text
    assert "Shared Extensions:" not in text
    assert "Local-only Extensions:" not in text
    # Row ordering
    positions = {
        name: text.index(name) for name in ["gonly", "shared1", "shared2", "local1", "local2"]
    }
    assert (
        positions["gonly"]
        < positions["shared1"]
        < positions["shared2"]
        < positions["local1"]
        < positions["local2"]
    )
    # Blacklisted status present
    assert "blacklisted" in text
