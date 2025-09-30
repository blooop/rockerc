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


def test_aggregate_with_invalid_tokens(capsys):
    """Test aggregates containing invalid or incomplete extension names.

    Verify the normalization logic handles invalid tokens correctly:
    - Valid aggregates (like "nvidia - x11 -") are expanded to individual tokens
    - Invalid aggregates (with special chars, leading dashes) remain as-is
    """
    final_args = ["nvidia", "x11"]
    original_global_args = ["nvidia"]
    # Aggregates with invalid tokens: empty parts, special chars, non-alphanumeric
    original_project_args = [
        "nvidia - x11 - ",  # trailing empty - VALID, should expand
        " - leading - empty",  # leading empty - INVALID, stays as-is
        "valid1 - @invalid! - valid2",  # special chars - INVALID, stays as-is
        "a - - - b",  # multiple separators - INVALID (dash alone not alphanumeric), stays as-is
    ]
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
    # Valid expanded tokens should appear
    assert "nvidia" in out
    assert "x11" in out

    # The valid aggregate "nvidia - x11 -" should be expanded, so it shouldn't appear as-is
    assert "nvidia - x11 -" not in out

    # Invalid aggregates remain as-is and should appear in the output
    assert " - leading - empty" in out
    assert "valid1 - @invalid! - valid2" in out
    assert "a - - - b" in out
