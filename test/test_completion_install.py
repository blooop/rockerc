"""Tests for completion installation helpers."""

from rockerc.completion import install_all_completions
from rockerc.renv import install_shell_completion


def test_install_shell_completion_refreshes(tmp_path, monkeypatch):
    """Existing renv completion block is replaced by a sourced file."""
    completion_file = tmp_path / "completions.sh"
    monkeypatch.setenv("ROCKERC_COMPLETION_FILE", str(completion_file))

    rc_file = tmp_path / "bashrc"
    rc_file.write_text(
        "# renv completion\noutdated\ncomplete -F _renv_completion renvvsc\n",
        encoding="utf-8",
    )

    assert install_shell_completion(rc_path=rc_file) == 0

    rc_content = rc_file.read_text(encoding="utf-8")
    # Inline blocks removed in favor of a small sourced block
    assert "# renv completion" not in rc_content
    assert "# >>> rockerc completions >>>" in rc_content
    assert str(completion_file) in rc_content

    completions_content = completion_file.read_text(encoding="utf-8")
    assert "outdated" not in completions_content
    assert completions_content.count("# renv completion") == 1
    assert completions_content.count("# rockerc completion") == 1
    assert completions_content.count("# aid completion") == 1
    assert "-exec basename {} \\;" in completions_content
    assert "\\\\;" not in completions_content


def test_install_all_completions_idempotent(tmp_path, monkeypatch):
    """rockerc --install refreshes source block and overwrites completion file."""
    completion_file = tmp_path / "completions.sh"
    monkeypatch.setenv("ROCKERC_COMPLETION_FILE", str(completion_file))
    rc_file = tmp_path / "bashrc"

    assert install_all_completions(rc_file) == 0
    first_rc = rc_file.read_text(encoding="utf-8")
    first_completion = completion_file.read_text(encoding="utf-8")

    assert first_rc.count("# >>> rockerc completions >>>") == 1
    assert f'source "{completion_file}"' in first_rc
    assert first_completion.count("# rockerc completion") == 1
    assert first_completion.count("# renv completion") == 1
    assert first_completion.count("# aid completion") == 1

    # Overwrite with stale content to confirm reinstall replaces it.
    completion_file.write_text("stale\n", encoding="utf-8")
    assert install_all_completions(rc_file) == 0

    second_rc = rc_file.read_text(encoding="utf-8")
    second_completion = completion_file.read_text(encoding="utf-8")

    assert second_rc.count("# >>> rockerc completions >>>") == 1
    assert f'source "{completion_file}"' in second_rc
    assert second_completion != "stale\n"
    assert second_completion.count("# rockerc completion") == 1
    assert second_completion.count("# renv completion") == 1
    assert second_completion.count("# aid completion") == 1
    assert "-exec basename {} \\;" in second_completion
    assert "\\\\;" not in second_completion
