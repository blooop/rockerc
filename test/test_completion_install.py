"""Tests for completion installation helpers."""

from rockerc.completion import install_all_completions
from rockerc.renv import install_shell_completion


def test_install_shell_completion_refreshes(tmp_path):
    """Existing renv completion block is replaced in-place."""
    rc_file = tmp_path / "bashrc"
    rc_file.write_text(
        "# renv completion\noutdated\ncomplete -F _renv_completion renvvsc\n",
        encoding="utf-8",
    )

    assert install_shell_completion(rc_path=rc_file) == 0

    content = rc_file.read_text(encoding="utf-8")
    assert "outdated" not in content
    assert content.count("# renv completion") == 1
    assert "complete -F _renv_completion renvvsc" in content
    assert content.strip().endswith("# end renv completion")


def test_install_all_completions_idempotent(tmp_path):
    """rockerc --install refreshes all completion blocks without duplication."""
    rc_file = tmp_path / "bashrc"

    assert install_all_completions(rc_file) == 0
    first = rc_file.read_text(encoding="utf-8")
    assert "# rockerc completion" in first
    assert "# renv completion" in first
    assert "# aid completion" in first

    assert install_all_completions(rc_file) == 0
    second = rc_file.read_text(encoding="utf-8")
    assert second.count("# rockerc completion") == 1
    assert second.count("# renv completion") == 1
    assert second.count("# aid completion") == 1
