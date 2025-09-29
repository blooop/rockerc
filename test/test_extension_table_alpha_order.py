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
