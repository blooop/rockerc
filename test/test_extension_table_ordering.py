from rockerc.rockerc import render_extension_table


def test_row_group_ordering_with_blacklist(capsys):
    """Ensure ordering strictly follows: Global-only, Shared, Local-only.

    Blacklisted extensions must appear in their natural group positions, not
    segregated. We construct:
      global args:   gonly, shared1, shared2
      project args:  shared1, local1, shared2, local2
      blacklist:     shared1, local2

    Groups expected:
      Global-only: gonly
      Shared:      shared1 (blacklisted), shared2
      Local-only:  local1, local2 (blacklisted)

    Final merged args after blacklist (what rocker would actually load):
      gonly, shared2, local1
    removed_by_blacklist:
      shared1, local2
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

    out = capsys.readouterr().out
    # We operate in plain (non-color) mode under pytest capture, so simple substring index works.
    expected_order = ["gonly", "shared1", "shared2", "local1", "local2"]
    positions = {name: out.index(name) for name in expected_order}
    # Assert strict ordering
    assert (
        positions["gonly"]
        < positions["shared1"]
        < positions["shared2"]
        < positions["local1"]
        < positions["local2"]
    )
    # Blacklisted extensions should have status 'blacklisted' and NOT create an extra group label
    assert "blacklisted" in out
    assert "Blacklist" not in out  # no separate header/group name
    # The redundant 'Extension' column header must be absent after spec clarification
    header_line = out.splitlines()[1] if len(out.splitlines()) > 1 else ""
    assert "Extension" not in header_line
