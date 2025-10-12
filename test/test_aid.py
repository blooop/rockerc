"""Tests for aid (AI Develop) command functionality."""

import pytest

from rockerc.aid import (
    build_ai_command,
    generate_aid_completion,
    install_aid_completion,
    parse_aid_args,
)


def test_parse_aid_args_default_gemini():
    """Test that gemini is the default agent."""
    args = parse_aid_args(["owner/repo", "test", "prompt"])
    assert args.agent == "gemini"
    assert args.repo_spec == "owner/repo"
    assert args.prompt == ["test", "prompt"]


def test_parse_aid_args_claude():
    """Test claude agent selection."""
    args = parse_aid_args(["--claude", "owner/repo", "test", "prompt"])
    assert args.agent == "claude"
    assert args.repo_spec == "owner/repo"
    assert args.prompt == ["test", "prompt"]


def test_parse_aid_args_codex():
    """Test codex agent selection."""
    args = parse_aid_args(["--codex", "owner/repo@branch", "complex", "multi", "word", "prompt"])
    assert args.agent == "codex"
    assert args.repo_spec == "owner/repo@branch"
    assert args.prompt == ["complex", "multi", "word", "prompt"]


def test_parse_aid_args_flash_flag():
    """Test flash flag parsing."""
    args = parse_aid_args(["--flash", "owner/repo", "prompt"])
    assert args.flash is True


def test_parse_aid_args_flash_short_flag():
    """Test short flash flag parsing."""
    args = parse_aid_args(["-f", "owner/repo", "prompt"])
    assert args.flash is True


def test_build_ai_command_gemini():
    """Test gemini command construction."""
    command = build_ai_command("gemini", "test prompt")
    assert len(command) == 3
    assert command[0] == "gemini"
    assert command[1] == "--prompt-interactive"
    assert "test prompt" in command[2]


def test_build_ai_command_claude():
    """Test claude command construction."""
    command = build_ai_command("claude", "test prompt")
    assert len(command) == 3
    assert command[0] == "bash"
    assert command[1] == "-c"
    assert "claude" in command[2]
    assert "test prompt" in command[2]


def test_build_ai_command_codex():
    """Test codex command construction."""
    command = build_ai_command("codex", "test prompt")
    assert len(command) == 3
    assert command[0] == "bash"
    assert command[1] == "-c"
    assert "openai" in command[2]
    assert "test prompt" in command[2]


def test_build_ai_command_quote_escaping():
    """Test that single quotes in prompts are properly escaped."""
    command = build_ai_command("gemini", "test 'quoted' prompt")
    # Check that the command contains properly escaped quotes
    assert "test '\"'\"'quoted'\"'\"' prompt" in command[2] or "test" in command[2]


def test_build_ai_command_invalid_agent():
    """Test that invalid agent raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported AI agent"):
        build_ai_command("invalid_agent", "test prompt")


def test_parse_aid_args_missing_arguments():
    """Test that missing arguments raises SystemExit (argparse behavior)."""
    with pytest.raises(SystemExit):
        parse_aid_args(["owner/repo"])  # Missing prompt


def test_parse_aid_args_mutually_exclusive_agents():
    """Test that multiple agents can't be specified."""
    with pytest.raises(SystemExit):
        parse_aid_args(["--gemini", "--claude", "owner/repo", "prompt"])


def test_parse_aid_args_repo_with_subfolder():
    """Test parsing repo spec with subfolder."""
    args = parse_aid_args(["owner/repo#subfolder", "test", "prompt"])
    assert args.repo_spec == "owner/repo#subfolder"
    assert args.prompt == ["test", "prompt"]


def test_build_ai_command_flash_adds_model():
    """Gemini flash flag adds model argument."""
    command = build_ai_command("gemini", "prompt", flash=True)
    assert "--model" in command
    assert "gemini-2.5-flash" in command


def test_build_ai_command_flash_ignored_for_non_gemini():
    """Flash flag is ignored for non-gemini agents."""
    command = build_ai_command("claude", "prompt", flash=True)
    assert "--model" not in command


def test_generate_aid_completion_only_bash():
    """Only bash completion is supported."""
    with pytest.raises(ValueError, match="Only bash completion"):
        generate_aid_completion("zsh")


def test_install_aid_completion_overwrites_existing(tmp_path, monkeypatch):
    """Ensure install overwrites previous installation."""
    completion_file = tmp_path / "completions.sh"
    monkeypatch.setenv("ROCKERC_COMPLETION_FILE", str(completion_file))

    rc_file = tmp_path / "bashrc"
    rc_file.write_text(
        "# aid completion\nold content\ncomplete -F _aid_completion aid\n",
        encoding="utf-8",
    )
    result = install_aid_completion(rc_path=rc_file)
    assert result == 0
    written = rc_file.read_text(encoding="utf-8")
    assert "# aid completion" not in written
    assert "complete -F _aid_completion aid" not in written
    assert "# >>> rockerc completions >>>" in written
    assert str(completion_file) in written

    completions_content = completion_file.read_text(encoding="utf-8")
    assert completions_content.count("# aid completion") == 1
    assert "old content" not in completions_content


def test_install_aid_completion_creates_file(tmp_path, monkeypatch):
    """Install should create rc file when missing."""
    completion_file = tmp_path / "completions.sh"
    monkeypatch.setenv("ROCKERC_COMPLETION_FILE", str(completion_file))

    rc_file = tmp_path / "bashrc"
    result = install_aid_completion(rc_path=rc_file)
    assert result == 0
    assert rc_file.exists()
    content = rc_file.read_text(encoding="utf-8")
    assert "# >>> rockerc completions >>>" in content
    assert str(completion_file) in content
    completions_content = completion_file.read_text(encoding="utf-8")
    assert "# aid completion" in completions_content
