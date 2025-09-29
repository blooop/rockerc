from rockerc.rockerc import render_extension_table


def test_aggregate_token_normalization(capsys):
    # Simulate metadata where project args accidentally contain an aggregated string
    final_args = ["nvidia", "x11", "user"]
    original_global_args = ["nvidia", "x11"]
    original_project_args = ["nvidia - x11 - user"]  # aggregated artifact
    blacklist = []
    removed = []
    render_extension_table(
        final_args,
        original_global_args=original_global_args,
        original_project_args=original_project_args,
        blacklist=blacklist,
        removed_by_blacklist=removed,
    )
    out = capsys.readouterr().out
    # Each extension should appear on its own line in the Extension column; aggregated line absent
    assert "nvidia - x11 - user" not in out
    assert out.count("nvidia") >= 1
    assert out.count("x11") >= 1
    assert out.count("user") >= 1
